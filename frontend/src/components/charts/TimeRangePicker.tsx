/**
 * Time range picker component using React, Shadcn UI, and Jotai state management.
 *
 * Provides time range selection interface for telemetry data visualization
 * with preset options and custom range selection capabilities.
 */

'use client';

import React, { useState } from 'react';
import { useAtom } from 'jotai';
import { Clock, Calendar, RefreshCw, Play, Pause, Settings } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { Input } from '@/components/ui/input';

import {
  selectedTimeRangeAtom,
  setTimeRangeAtom,
  isRealTimeEnabledAtom,
  toggleRealTimeAtom,
  refreshTelemetryAtom,
  selectedFieldsAtom,
  setSelectedFieldsAtom,
  TIME_RANGES,
  TimeRangeKey,
  TELEMETRY_FIELDS,
} from '@/state/telemetryAtoms';

import { selectedDeviceAtom } from '@/state/hierarchyAtoms';

interface TimeRangePickerProps {
  className?: string;
  variant?: 'default' | 'compact' | 'full';
  showRealTimeToggle?: boolean;
  showRefreshButton?: boolean;
  showFieldSelector?: boolean;
  showCustomRange?: boolean;
}

export default function TimeRangePicker({
  className = '',
  variant = 'default',
  showRealTimeToggle = true,
  showRefreshButton = true,
  showFieldSelector = true,
  showCustomRange = false
}: TimeRangePickerProps) {
  // State atoms
  const [selectedTimeRange] = useAtom(selectedTimeRangeAtom);
  const [, setTimeRange] = useAtom(setTimeRangeAtom);
  const [isRealTimeEnabled] = useAtom(isRealTimeEnabledAtom);
  const [, toggleRealTime] = useAtom(toggleRealTimeAtom);
  const [, refreshTelemetry] = useAtom(refreshTelemetryAtom);
  const [selectedFields] = useAtom(selectedFieldsAtom);
  const [, setSelectedFields] = useAtom(setSelectedFieldsAtom);
  const [selectedDevice] = useAtom(selectedDeviceAtom);

  // Local state for custom range
  const [customStartDate, setCustomStartDate] = useState<Date>();
  const [customEndDate, setCustomEndDate] = useState<Date>();
  const [showCustomRangePicker, setShowCustomRangePicker] = useState(false);

  const handleTimeRangeChange = (value: TimeRangeKey) => {
    setTimeRange(value);
  };

  const handleRefresh = () => {
    refreshTelemetry();
  };

  const handleToggleRealTime = () => {
    toggleRealTime();
  };

  const handleFieldToggle = (fieldName: string) => {
    const newFields = selectedFields.includes(fieldName)
      ? selectedFields.filter(f => f !== fieldName)
      : [...selectedFields, fieldName];
    setSelectedFields(newFields);
  };

  const handleSelectAllFields = () => {
    setSelectedFields(Object.keys(TELEMETRY_FIELDS));
  };

  const handleDeselectAllFields = () => {
    setSelectedFields([]);
  };

  if (variant === 'compact') {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <Select value={selectedTimeRange} onValueChange={handleTimeRangeChange}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(TIME_RANGES).map(([key, range]) => (
              <SelectItem key={key} value={key}>
                {range.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {showRealTimeToggle && (
          <Button
            variant={isRealTimeEnabled ? "default" : "outline"}
            size="sm"
            onClick={handleToggleRealTime}
            disabled={!selectedDevice}
          >
            {isRealTimeEnabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </Button>
        )}

        {showRefreshButton && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={!selectedDevice}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        )}
      </div>
    );
  }

  if (variant === 'full') {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Clock className="h-5 w-5" />
            <span>Time Range & Data Controls</span>
          </CardTitle>
          <CardDescription>
            Configure time range, real-time updates, and telemetry fields
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Time Range Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Time Range</Label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {Object.entries(TIME_RANGES).map(([key, range]) => (
                <Button
                  key={key}
                  variant={selectedTimeRange === key ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleTimeRangeChange(key as TimeRangeKey)}
                  className="justify-start"
                >
                  {range.label}
                </Button>
              ))}
            </div>
            {showCustomRange && (
              <div className="pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowCustomRangePicker(!showCustomRangePicker)}
                >
                  <Calendar className="h-4 w-4 mr-2" />
                  Custom Range
                </Button>
              </div>
            )}
          </div>

          <Separator />

          {/* Real-time Controls */}
          {showRealTimeToggle && (
            <div className="space-y-3">
              <Label className="text-sm font-medium">Real-time Updates</Label>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={isRealTimeEnabled}
                    onCheckedChange={handleToggleRealTime}
                    disabled={!selectedDevice}
                  />
                  <Label className="text-sm">
                    {isRealTimeEnabled ? 'Live data streaming' : 'Historical data only'}
                  </Label>
                  {isRealTimeEnabled && (
                    <Badge variant="secondary" className="text-xs">
                      Live
                    </Badge>
                  )}
                </div>
                {showRefreshButton && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRefresh}
                    disabled={!selectedDevice}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Field Selection */}
          {showFieldSelector && (
            <>
              <Separator />
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium">Telemetry Fields</Label>
                  <div className="flex space-x-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleSelectAllFields}
                    >
                      Select All
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleDeselectAllFields}
                    >
                      None
                    </Button>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(TELEMETRY_FIELDS).map(([fieldName, field]) => (
                    <div
                      key={fieldName}
                      className="flex items-center space-x-2 p-2 border rounded-lg cursor-pointer hover:bg-muted/50"
                      onClick={() => handleFieldToggle(fieldName)}
                    >
                      <input
                        type="checkbox"
                        checked={selectedFields.includes(fieldName)}
                        onChange={() => handleFieldToggle(fieldName)}
                        className="rounded"
                      />
                      <div className="flex items-center space-x-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: field.color }}
                        />
                        <div>
                          <p className="text-sm font-medium">{field.label}</p>
                          <p className="text-xs text-muted-foreground">{field.unit}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Current Selection Summary */}
          <Separator />
          <div className="space-y-2">
            <Label className="text-sm font-medium">Current Selection</Label>
            <div className="text-sm text-muted-foreground space-y-1">
              <p>Range: {TIME_RANGES[selectedTimeRange].label}</p>
              <p>Fields: {selectedFields.length} of {Object.keys(TELEMETRY_FIELDS).length} selected</p>
              <p>Updates: {isRealTimeEnabled ? 'Real-time enabled' : 'Historical only'}</p>
              {selectedDevice && (
                <p>Device: {selectedDevice.name}</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Default variant
  return (
    <div className={`flex items-center justify-between ${className}`}>
      <div className="flex items-center space-x-4">
        {/* Time Range Selector */}
        <div className="flex items-center space-x-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <Select value={selectedTimeRange} onValueChange={handleTimeRangeChange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(TIME_RANGES).map(([key, range]) => (
                <SelectItem key={key} value={key}>
                  {range.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Real-time Toggle */}
        {showRealTimeToggle && (
          <div className="flex items-center space-x-2">
            <Switch
              checked={isRealTimeEnabled}
              onCheckedChange={handleToggleRealTime}
              disabled={!selectedDevice}
            />
            <Label className="text-sm">
              Real-time
            </Label>
            {isRealTimeEnabled && (
              <Badge variant="secondary" className="text-xs">
                Live
              </Badge>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center space-x-2">
        {/* Field Selector */}
        {showFieldSelector && (
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings className="h-4 w-4 mr-2" />
                Fields ({selectedFields.length})
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">Telemetry Fields</h4>
                  <div className="flex space-x-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleSelectAllFields}
                    >
                      All
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleDeselectAllFields}
                    >
                      None
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  {Object.entries(TELEMETRY_FIELDS).map(([fieldName, field]) => (
                    <div
                      key={fieldName}
                      className="flex items-center space-x-2 p-2 border rounded cursor-pointer hover:bg-muted/50"
                      onClick={() => handleFieldToggle(fieldName)}
                    >
                      <input
                        type="checkbox"
                        checked={selectedFields.includes(fieldName)}
                        onChange={() => handleFieldToggle(fieldName)}
                        className="rounded"
                      />
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: field.color }}
                      />
                      <div className="flex-1">
                        <p className="text-sm font-medium">{field.label}</p>
                        <p className="text-xs text-muted-foreground">{field.unit}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </PopoverContent>
          </Popover>
        )}

        {/* Refresh Button */}
        {showRefreshButton && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={!selectedDevice}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}