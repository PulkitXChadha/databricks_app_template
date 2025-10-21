/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TimeSeriesDataPoint } from './TimeSeriesDataPoint';
/**
 * Response for time-series metrics endpoint.
 */
export type TimeSeriesMetricsResponse = {
    /**
     * Time range covered
     */
    time_range: string;
    /**
     * Time bucket interval (hourly, daily)
     */
    interval: string;
    /**
     * Time-series data points
     */
    data_points: Array<TimeSeriesDataPoint>;
};

