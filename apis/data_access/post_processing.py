#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# OpenBACH is a generic testbed able to control/configure multiple
# network/physical entities (under test) and collect data from them.
# It is composed of an Auditorium (HMIs), a Controller, a Collector
# and multiple Agents (one for each network entity that wants to be
# tested).
#
#
# Copyright © 2016-2019 CNES
#
#
# This file is part of the OpenBACH testbed.
#
#
# OpenBACH is a free software : you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY, without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

"""Utilities to present data from an InfluxDB server and optionaly plot them.
"""

__author__ = 'Mathias ETTINGER <mettinger@toulouse.viveris.com>'
__all__ = ['save', 'Statistics']

import pickle
import itertools
from functools import partial
from contextlib import suppress

import yaml
import numpy as np
import pandas as pd

from .influxdb_tools import (
        tags_to_condition, select_query,
        InfluxDBCommunicator, Operator,
        ConditionTag, ConditionAnd, ConditionOr,
)


DEFAULT_COLLECTOR_FILEPATH = '/opt/openbach/agent/collector.yml'


def _identity(x):
    return x


def _column_name_serializer(name):
    return '_'.join(map(str, name))


def _prepare_columns(df, columns):
    df = df.sort_values(['suffix', 'statistic'], axis=1)
    df.columns = [next(columns, name) or name for name in df.columns]
    return df


def influx_to_pandas(response):
    for result in response.get('results', []):
        for serie in result.get('series', []):
            with suppress(KeyError):
                yield pd.DataFrame(serie['values'], columns=serie['columns'])


def compute_histogram(bins):
    def _compute_histogram(series):
        histogram, _ = np.histogram(series.dropna(), bins)
        return histogram / histogram.sum()
    return _compute_histogram


def save(figure, filename, use_pickle=False):
    if use_pickle:
        with open(filename, 'wb') as storage:
            pickle.dump(figure, storage)
    else:
        artists = [
                axis.legend(loc='center left', bbox_to_anchor=(1., .5))
                for axis in figure.axes
                if axis.get_legend()
        ]
        figure.savefig(filename, additional_artists=[artists], bbox_inches='tight')


class Statistics(InfluxDBCommunicator):
    @classmethod
    def from_default_collector(cls, filepath=DEFAULT_COLLECTOR_FILEPATH):
        with open(filepath) as f:
            collector = yaml.load(f)

        influx = collector.get('stats', {})
        return cls(
                collector['address'],
                influx.get('query', 8086),
                influx.get('database', 'openbach'),
                influx.get('precision', 'ms'))

    @property
    def origin(self):
        with suppress(AttributeError):
            return self._origin

    @origin.setter
    def origin(self, value):
        if value is not None and not isinstance(value, int):
            raise TypeError('origin should be None or a timestamp in milliseconds')
        self._origin = value

    def _raw_influx_data(
            self, job=None, scenario=None, agent=None, job_instances=(),
            suffix=None, fields=None, condition=None):
        conditions = tags_to_condition(scenario, agent, None, suffix, condition)
        instances = [
                ConditionTag('@job_instance_id', Operator.Equal, job_id)
                for job_id in job_instances
        ]

        if not conditions and not instances:
            _condition = None
        elif conditions and not instances:
            _condition = conditions
        elif not conditions and instances:
            _condition = ConditionOr(*instances)
        else:
            _condition = ConditionAnd(conditions, ConditionOr(*instances))
        return self.sql_query(select_query(job, fields, _condition))

    def _parse_dataframes(self, response):
        offset = self.origin
        names = ['job', 'scenario', 'agent', 'suffix', 'statistic']
        for df in influx_to_pandas(response):
            converters = dict.fromkeys(df.columns, partial(pd.to_numeric, errors='coerce'))
            converters.pop('@owner_scenario_instance_id')
            converters.pop('@suffix', None)
            converters['@agent_name'] = _identity

            converted = [convert(df[column]) for column, convert in converters.items()]
            if '@suffix' in df:
                converted.append(df['@suffix'].fillna(''))
            else:
                converted.append(pd.Series('', index=df.index, name='@suffix'))
            df = pd.concat(converted, axis=1)

            df.set_index(['@job_instance_id', '@scenario_instance_id', '@agent_name', '@suffix'], inplace=True)
            for index in df.index.unique():
                extract = df.xs(index)
                if isinstance(extract, pd.Series):
                    extract = pd.DataFrame(extract.to_dict(), index=[0])
                section = extract.reset_index(drop=True).dropna(axis=1, how='all')
                section['time'] -= section.time[0] if offset is None else offset
                section.set_index('time', inplace=True)
                section.index.name = 'Time (ms)'
                section.reindex(columns=section.columns.sort_values())
                section.columns = pd.MultiIndex.from_tuples([index + (name,) for name in section.columns], names=names)
                yield section

    def fetch(
            self, job=None, scenario=None, agent=None, job_instances=(),
            suffix=None, fields=None, condition=None):
        data = self._raw_influx_data(job, scenario, agent, job_instances, suffix, fields, condition)
        yield from (_Plot(df) for df in self._parse_dataframes(data))

    def fetch_all(
            self, job=None, scenario=None, agent=None, job_instances=(),
            suffix=None, fields=None, condition=None, columns=None):
        data = self._raw_influx_data(job, scenario, agent, job_instances, suffix, fields, condition)
        df = pd.concat(self._parse_dataframes(data), axis=1)
        if not job_instances or columns is None:
            return _Plot(df)
        columns = iter(columns)
        return _Plot(pd.concat([_prepare_columns(df[id], columns) for id in job_instances if id in df], axis=1))


class _Plot:
    def __init__(self, dataframe):
        self.dataframe = dataframe
        self.df = dataframe[dataframe.index >= 0]

    def time_series(self):
        df = self.dataframe.interpolate()
        return df[df.index >= 0]

    def histogram(self, buckets):
        r_min = self.df.min().min()
        r_max = self.df.max().max()
        bins = np.linspace(r_min, r_max, buckets + 1)
        histogram = compute_histogram(bins)
        df = self.df.apply(histogram)
        bins = (bins + np.roll(bins, -1)) / 2
        df.index = bins[:buckets]
        return df

    def temporal_binning_statistics(self, stat_name=None, index=None,
            time_aggregation='hour', percentiles=[.05, .25, .5, .75, .95]):
        if stat_name is not None:
            for col_name, col in self.df.iteritems():
                if col_name[4] == stat_name:
                    df = col
                    break
        elif index is not None:
            df = self.df.iloc[:, index]
        else:
            df = self.df
        dates = pd.to_datetime(df.index, unit='ms')
        df.index = dates.values
        if time_aggregation == 'year' :
            groups = df.groupby(df.index.year)
        elif time_aggregation == 'month' :
            groups = df.groupby(df.index.month)
        elif time_aggregation == 'day' :
            groups = df.groupby(df.index.day)
        elif time_aggregation == 'hour' :
            groups = df.groupby(df.index.hour)
        elif time_aggregation == 'minute' :
            groups = df.groupby(df.index.minute)
        elif time_aggregation == 'second' :
            groups = df.groupby(df.index.second)
        else:
            raise ValueError('No valid time aggregation value.')
        stats = groups.describe(percentiles=percentiles)
        stats.index.name = 'Time ({}s)'.format(time_aggregation)
        return stats.drop(columns=['count'])
        
    def cumulative_histogram(self, buckets):
        return self.histogram(buckets).cumsum()

    def comparison(self):
        mean = self.df.mean()
        std = self.df.std().fillna(0)
        df = pd.concat([mean, std], axis=1)
        df.columns = ['Ε', 'δ']
        return df

    def plot_time_series(self, axis=None, secondary_title=None, legend=True):
        axis = self.time_series().plot(ax=axis, legend=legend)
        if secondary_title is not None:
            axis.set_ylabel(secondary_title)
        return axis

    def plot_kde(self, axis=None, secondary_title=None, legend=True):
        axis = self.df.plot.kde(ax=axis, legend=legend)
        if secondary_title is not None:
            axis.set_xlabel(secondary_title)
        return axis

    def plot_histogram(self, axis=None, secondary_title=None, bins=100, legend=True):
        axis = self.histogram(bins).plot(ax=axis, ylim=[-0.01, 1.01], legend=legend)
        if secondary_title is not None:
            axis.set_xlabel(secondary_title)
        return axis

    def plot_temporal_binning_statistics(self, stat_name=None, index=None,
            time_aggregation='hour', percentiles=[[5, 95], [25, 75]],
            axis=None, secondary_title=None, legend=True, median=True,
            average=True, deviation=True, boundaries=True, min_max=True):
        colors = ['#ffad60', '#ffdae0']
        format_percentiles = [p/100 for pair in percentiles for p in pair] if percentiles else []
        stats = self.temporal_binning_statistics(stat_name, index, time_aggregation, format_percentiles)
        if average:
            axis.plot(stats.index, stats['mean'], color='#005b96', label='average')
        if median:
            axis.plot(stats.index, stats['50%'], color='#be68be', label='median')
        if boundaries:
            axis.plot(stats.index, stats['min'], color='g', linewidth=1)
            axis.plot(stats.index, stats['max'], color='#e50000', linewidth=1)
        if min_max:
            axis.fill_between(stats.index, stats['min'], stats['max'], color='#39c9bb', label='min-max')
        if percentiles:
            percentiles.sort(key=lambda x: abs(x[0]-x[1]), reverse=True)
            for index, pair in enumerate(percentiles):
                pair.sort()
                axis.fill_between(stats.index, stats['{}%'.format(pair[0])],
                        stats['{}%'.format(pair[1])], color=colors[index],
                        label='{}%-{}%'.format(pair[0], pair[1]))
        if deviation:        
            std = stats.pop('std')
            axis.errorbar(stats.index, stats['mean'], std, uplims=True,
                    lolims=True, color='#005b96', elinewidth=1, label="deviation")
        if legend:
            axis.legend()
        axis.set_xlabel(stats.index.name)
        if secondary_title is not None:
            axis.set_ylabel(secondary_title)
        return axis

    def plot_cumulative_histogram(self, axis=None, secondary_title=None, bins=100, legend=True):
        axis = self.cumulative_histogram(bins).plot(ax=axis, ylim=[-0.01, 1.01], legend=legend)
        if secondary_title is not None:
            axis.set_xlabel(secondary_title)
        return axis

    def plot_comparison(self, axis=None, secondary_title=None, legend=True):
        df = self.comparison()
        axis = df.Ε.plot.bar(ax=axis, yerr=df.δ, rot=30, legend=legend)
        if secondary_title is not None:
            axis.set_ylabel(secondary_title)
        return axis
