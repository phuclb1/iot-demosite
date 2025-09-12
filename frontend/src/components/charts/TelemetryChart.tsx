'use client'

import React from 'react'
import { BaseChart } from './BaseChart'
import { IVChartProps } from '@visactor/vchart'

interface TelemetryDataPoint {
  timestamp: string
  value: number
  device_id: string
}

interface TelemetryChartProps {
  data: TelemetryDataPoint[]
  title: string
  valueField: 'vibration' | 'temperature' | 'power' | 'electricity'
  unit: string
  color?: string
  className?: string
  height?: number
}

export function TelemetryChart({
  data,
  title,
  valueField,
  unit,
  color = '#3b82f6',
  className,
  height = 300,
}: TelemetryChartProps) {
  const chartSpec: IVChartProps['spec'] = {
    type: 'line',
    data: [
      {
        values: data.map(point => ({
          x: new Date(point.timestamp).getTime(),
          y: point.value,
        })),
      },
    ],
    xField: 'x',
    yField: 'y',
    point: {
      visible: false,
    },
    line: {
      style: {
        stroke: color,
        lineWidth: 2,
      },
    },
    axes: [
      {
        orient: 'bottom',
        type: 'time',
        label: {
          style: {
            fontSize: 12,
            fill: '#666',
          },
        },
        tick: {
          tickSize: 4,
        },
        grid: {
          visible: true,
          style: {
            stroke: '#f0f0f0',
            lineWidth: 1,
          },
        },
      },
      {
        orient: 'left',
        type: 'linear',
        label: {
          style: {
            fontSize: 12,
            fill: '#666',
          },
        },
        tick: {
          tickSize: 4,
        },
        grid: {
          visible: true,
          style: {
            stroke: '#f0f0f0',
            lineWidth: 1,
          },
        },
        title: {
          visible: true,
          text: unit,
          style: {
            fontSize: 12,
            fill: '#333',
          },
        },
      },
    ],
    title: {
      visible: true,
      text: title,
      style: {
        fontSize: 16,
        fontWeight: 'bold',
        fill: '#333',
      },
    },
    legends: {
      visible: false,
    },
    background: 'transparent',
    padding: {
      top: 40,
      right: 20,
      bottom: 40,
      left: 60,
    },
    animation: {
      appear: {
        duration: 1000,
        easing: 'easeInOutQuart',
      },
      update: {
        duration: 500,
        easing: 'easeInOutQuart',
      },
    },
    hover: {
      enable: true,
    },
    crosshair: {
      xField: {
        visible: true,
        line: {
          style: {
            stroke: '#999',
            lineWidth: 1,
            lineDash: [4, 4],
          },
        },
      },
      yField: {
        visible: true,
        line: {
          style: {
            stroke: '#999',
            lineWidth: 1,
            lineDash: [4, 4],
          },
        },
      },
    },
    tooltip: {
      visible: true,
      mark: {
        title: {
          value: title,
        },
        content: [
          {
            key: 'Time',
            value: (datum: any) => new Date(datum.x).toLocaleString(),
          },
          {
            key: 'Value',
            value: (datum: any) => `${datum.y.toFixed(2)} ${unit}`,
          },
        ],
      },
    },
  }

  return <BaseChart spec={chartSpec} className={className} height={height} />
}

export default TelemetryChart