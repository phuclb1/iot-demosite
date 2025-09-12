'use client'

import React from 'react'
import { VChart } from '@visactor/react-vchart'
import { IVChartProps } from '@visactor/vchart'

interface BaseChartProps {
  spec: IVChartProps['spec']
  className?: string
  height?: number
  width?: number
}

export function BaseChart({ spec, className, height = 300, width }: BaseChartProps) {
  return (
    <div className={className}>
      <VChart
        spec={spec}
        option={{
          mode: 'desktop-browser',
          animation: true,
        }}
        height={height}
        width={width}
      />
    </div>
  )
}