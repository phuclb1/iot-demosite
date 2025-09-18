/**
 * Area selector component using React, Shadcn UI, and Jotai state management.
 *
 * Provides area selection interface with search, filtering,
 * and area management capabilities within a site.
 */

'use client';

import React, { useState } from 'react';
import { useAtom } from 'jotai';
import { Check, ChevronsUpDown, Grid3X3, Search, Plus, Settings, Users, Activity } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';

import {
  selectedSiteIdAtom,
  selectedSiteAtom,
} from '@/state/hierarchyAtoms';

import {
  areasListAtom,
  selectedAreaIdAtom,
  selectedAreaAtom,
  selectAreaAtom,
  hierarchyIsLoadingAtom,
  hierarchyHasErrorAtom,
  refreshAreasAtom,
} from '@/state/hierarchyAtoms';

import { hasAdminRoleAtom, hasOperatorRoleAtom, userAtom } from '@/state/authAtoms';

interface AreaSelectorProps {
  className?: string;
  showStats?: boolean;
  showSearch?: boolean;
  showManagement?: boolean;
  variant?: 'default' | 'compact' | 'card';
}

export default function AreaSelector({
  className = '',
  showStats = true,
  showSearch = true,
  showManagement = false,
  variant = 'default'
}: AreaSelectorProps) {
  // State atoms
  const [selectedSiteId] = useAtom(selectedSiteIdAtom);
  const [selectedSite] = useAtom(selectedSiteAtom);
  const [areas] = useAtom(areasListAtom);
  const [selectedAreaId] = useAtom(selectedAreaIdAtom);
  const [selectedArea] = useAtom(selectedAreaAtom);
  const [, selectArea] = useAtom(selectAreaAtom);
  const [isLoading] = useAtom(hierarchyIsLoadingAtom);
  const [hasError] = useAtom(hierarchyHasErrorAtom);
  const [, refreshAreas] = useAtom(refreshAreasAtom);

  // Permission atoms
  const [hasAdminRole] = useAtom(hasAdminRoleAtom);
  const [hasOperatorRole] = useAtom(hasOperatorRoleAtom);
  const [user] = useAtom(userAtom);

  // Local state
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Filter areas based on search
  const filteredAreas = areas.filter(area => {
    if (!searchQuery.trim()) return true;
    const searchLower = searchQuery.toLowerCase();
    return (
      area.name.toLowerCase().includes(searchLower) ||
      area.slug.toLowerCase().includes(searchLower) ||
      (area.description && area.description.toLowerCase().includes(searchLower))
    );
  });

  const handleSelect = (areaId: string) => {
    selectArea(areaId === selectedAreaId ? null : areaId);
    setOpen(false);
  };

  const handleRefresh = () => {
    refreshAreas();
  };

  // Don't render if no site is selected
  if (!selectedSiteId || !selectedSite) {
    return (
      <div className={`text-center py-8 text-muted-foreground ${className}`}>
        Please select a site first to view areas.
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={open}
              className="w-[200px] justify-between"
              disabled={isLoading || areas.length === 0}
            >
              {selectedArea ? (
                <span className="truncate">{selectedArea.name}</span>
              ) : (
                "Select area..."
              )}
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[200px] p-0">
            <Command>
              <CommandInput placeholder="Search areas..." />
              <CommandEmpty>No area found.</CommandEmpty>
              <CommandGroup>
                {areas.map((area) => (
                  <CommandItem
                    key={area.id}
                    value={area.id}
                    onSelect={handleSelect}
                  >
                    <Check
                      className={`mr-2 h-4 w-4 ${
                        selectedAreaId === area.id ? "opacity-100" : "opacity-0"
                      }`}
                    />
                    <div className="flex flex-col">
                      <span>{area.name}</span>
                      {area.description && (
                        <span className="text-xs text-muted-foreground truncate">
                          {area.description}
                        </span>
                      )}
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            </Command>
          </PopoverContent>
        </Popover>
      </div>
    );
  }

  if (variant === 'card') {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Grid3X3 className="h-5 w-5" />
            <span>Area</span>
          </CardTitle>
          {selectedArea && (
            <CardDescription>
              {selectedArea.description || 'No description available'}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <AreaSelector variant="compact" />
          {showStats && selectedArea && (
            <div className="mt-4 text-sm">
              <div>
                <Label className="text-muted-foreground">Created</Label>
                <p>{new Date(selectedArea.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Grid3X3 className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Areas</h3>
          {areas.length > 0 && (
            <Badge variant="secondary">{areas.length}</Badge>
          )}
        </div>

        {showManagement && (hasAdminRole || hasOperatorRole) && (
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isLoading}
            >
              Refresh
            </Button>
            {hasAdminRole && (
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Area
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Site context */}
      <div className="text-sm text-muted-foreground">
        Site: <span className="font-medium">{selectedSite.name}</span>
      </div>

      {/* Search */}
      {showSearch && areas.length > 5 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search areas..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      )}

      {/* Error state */}
      {hasError && (
        <Alert variant="destructive">
          <AlertDescription>
            Failed to load areas. Please try refreshing.
          </AlertDescription>
        </Alert>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-pulse space-y-2">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      )}

      {/* Area list */}
      {!isLoading && !hasError && (
        <div className="space-y-2">
          {filteredAreas.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery ? 'No areas found matching your search.' : 'No areas available in this site.'}
            </div>
          ) : (
            filteredAreas.map((area) => (
              <AreaCard
                key={area.id}
                area={area}
                isSelected={selectedAreaId === area.id}
                onSelect={handleSelect}
                showStats={showStats}
                showManagement={showManagement}
              />
            ))
          )}
        </div>
      )}

      {/* Selected area details */}
      {selectedArea && showStats && (
        <SelectedAreaDetails />
      )}
    </div>
  );
}

interface AreaCardProps {
  area: any;
  isSelected: boolean;
  onSelect: (areaId: string) => void;
  showStats: boolean;
  showManagement: boolean;
}

function AreaCard({
  area,
  isSelected,
  onSelect,
  showStats,
  showManagement
}: AreaCardProps) {
  const [hasAdminRole] = useAtom(hasAdminRoleAtom);
  const [hasOperatorRole] = useAtom(hasOperatorRoleAtom);

  return (
    <Card
      className={`cursor-pointer transition-colors ${
        isSelected ? 'ring-2 ring-primary bg-primary/5' : 'hover:bg-muted/50'
      }`}
      onClick={() => onSelect(area.id)}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h4 className="font-medium">{area.name}</h4>
              {isSelected && (
                <Badge variant="default" className="text-xs">
                  Selected
                </Badge>
              )}
            </div>
            {area.description && (
              <p className="text-sm text-muted-foreground mt-1">
                {area.description}
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Slug: {area.slug}
            </p>
          </div>

          {showManagement && (hasAdminRole || hasOperatorRole) && (
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle area settings
                }}
              >
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SelectedAreaDetails() {
  const [selectedArea] = useAtom(selectedAreaAtom);

  if (!selectedArea) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Grid3X3 className="h-5 w-5" />
          <span>{selectedArea.name}</span>
        </CardTitle>
        {selectedArea.description && (
          <CardDescription>{selectedArea.description}</CardDescription>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <Label className="text-muted-foreground">Slug</Label>
            <p className="font-mono text-xs">{selectedArea.slug}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Site ID</Label>
            <p className="font-mono text-xs">{selectedArea.site_id}</p>
          </div>
        </div>

        <Separator />

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <Label className="text-muted-foreground">Created</Label>
            <p>{new Date(selectedArea.created_at).toLocaleDateString()}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Updated</Label>
            <p>{new Date(selectedArea.updated_at).toLocaleDateString()}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}