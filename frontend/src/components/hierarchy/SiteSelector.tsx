/**
 * Site selector component using React, Shadcn UI, and Jotai state management.
 *
 * Provides site selection interface with search, filtering,
 * and site management capabilities within an organization.
 */

'use client';

import React, { useState } from 'react';
import { useAtom } from 'jotai';
import { Check, ChevronsUpDown, MapPin, Search, Plus, Settings, Building, Users, BarChart3 } from 'lucide-react';

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
  selectedOrganizationIdAtom,
  selectedOrganizationAtom,
} from '@/state/organizationAtoms';

import {
  sitesListAtom,
  selectedSiteIdAtom,
  selectedSiteAtom,
  selectSiteAtom,
  hierarchyIsLoadingAtom,
  hierarchyHasErrorAtom,
  refreshSitesAtom,
} from '@/state/hierarchyAtoms';

import { hasAdminRoleAtom, hasOperatorRoleAtom, userAtom } from '@/state/authAtoms';

interface SiteSelectorProps {
  className?: string;
  showStats?: boolean;
  showSearch?: boolean;
  showManagement?: boolean;
  variant?: 'default' | 'compact' | 'card';
}

export default function SiteSelector({
  className = '',
  showStats = true,
  showSearch = true,
  showManagement = false,
  variant = 'default'
}: SiteSelectorProps) {
  // State atoms
  const [selectedOrgId] = useAtom(selectedOrganizationIdAtom);
  const [selectedOrg] = useAtom(selectedOrganizationAtom);
  const [sites] = useAtom(sitesListAtom);
  const [selectedSiteId] = useAtom(selectedSiteIdAtom);
  const [selectedSite] = useAtom(selectedSiteAtom);
  const [, selectSite] = useAtom(selectSiteAtom);
  const [isLoading] = useAtom(hierarchyIsLoadingAtom);
  const [hasError] = useAtom(hierarchyHasErrorAtom);
  const [, refreshSites] = useAtom(refreshSitesAtom);

  // Permission atoms
  const [hasAdminRole] = useAtom(hasAdminRoleAtom);
  const [hasOperatorRole] = useAtom(hasOperatorRoleAtom);
  const [user] = useAtom(userAtom);

  // Local state
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Filter sites based on search
  const filteredSites = sites.filter(site => {
    if (!searchQuery.trim()) return true;
    const searchLower = searchQuery.toLowerCase();
    return (
      site.name.toLowerCase().includes(searchLower) ||
      site.slug.toLowerCase().includes(searchLower) ||
      (site.location && site.location.toLowerCase().includes(searchLower))
    );
  });

  const handleSelect = (siteId: string) => {
    selectSite(siteId === selectedSiteId ? null : siteId);
    setOpen(false);
  };

  const handleRefresh = () => {
    refreshSites();
  };

  // Don't render if no organization is selected
  if (!selectedOrgId || !selectedOrg) {
    return (
      <div className={`text-center py-8 text-muted-foreground ${className}`}>
        Please select an organization first to view sites.
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
              disabled={isLoading || sites.length === 0}
            >
              {selectedSite ? (
                <span className="truncate">{selectedSite.name}</span>
              ) : (
                "Select site..."
              )}
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[200px] p-0">
            <Command>
              <CommandInput placeholder="Search sites..." />
              <CommandEmpty>No site found.</CommandEmpty>
              <CommandGroup>
                {sites.map((site) => (
                  <CommandItem
                    key={site.id}
                    value={site.id}
                    onSelect={handleSelect}
                  >
                    <Check
                      className={`mr-2 h-4 w-4 ${
                        selectedSiteId === site.id ? "opacity-100" : "opacity-0"
                      }`}
                    />
                    <div className="flex flex-col">
                      <span>{site.name}</span>
                      {site.location && (
                        <span className="text-xs text-muted-foreground truncate">
                          {site.location}
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
            <MapPin className="h-5 w-5" />
            <span>Site</span>
          </CardTitle>
          {selectedSite && (
            <CardDescription>
              {selectedSite.location || 'No location specified'}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <SiteSelector variant="compact" />
          {showStats && selectedSite && (
            <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
              <div>
                <Label className="text-muted-foreground">Timezone</Label>
                <p>{selectedSite.timezone}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Created</Label>
                <p>{new Date(selectedSite.created_at).toLocaleDateString()}</p>
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
          <MapPin className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Sites</h3>
          {sites.length > 0 && (
            <Badge variant="secondary">{sites.length}</Badge>
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
                Add Site
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Organization context */}
      <div className="text-sm text-muted-foreground">
        Organization: <span className="font-medium">{selectedOrg.name}</span>
      </div>

      {/* Search */}
      {showSearch && sites.length > 5 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search sites..."
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
            Failed to load sites. Please try refreshing.
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

      {/* Site list */}
      {!isLoading && !hasError && (
        <div className="space-y-2">
          {filteredSites.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery ? 'No sites found matching your search.' : 'No sites available in this organization.'}
            </div>
          ) : (
            filteredSites.map((site) => (
              <SiteCard
                key={site.id}
                site={site}
                isSelected={selectedSiteId === site.id}
                onSelect={handleSelect}
                showStats={showStats}
                showManagement={showManagement}
              />
            ))
          )}
        </div>
      )}

      {/* Selected site details */}
      {selectedSite && showStats && (
        <SelectedSiteDetails />
      )}
    </div>
  );
}

interface SiteCardProps {
  site: any;
  isSelected: boolean;
  onSelect: (siteId: string) => void;
  showStats: boolean;
  showManagement: boolean;
}

function SiteCard({
  site,
  isSelected,
  onSelect,
  showStats,
  showManagement
}: SiteCardProps) {
  const [hasAdminRole] = useAtom(hasAdminRoleAtom);
  const [hasOperatorRole] = useAtom(hasOperatorRoleAtom);

  return (
    <Card
      className={`cursor-pointer transition-colors ${
        isSelected ? 'ring-2 ring-primary bg-primary/5' : 'hover:bg-muted/50'
      }`}
      onClick={() => onSelect(site.id)}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h4 className="font-medium">{site.name}</h4>
              {isSelected && (
                <Badge variant="default" className="text-xs">
                  Selected
                </Badge>
              )}
            </div>
            {site.location && (
              <p className="text-sm text-muted-foreground mt-1 flex items-center">
                <MapPin className="h-3 w-3 mr-1" />
                {site.location}
              </p>
            )}
            <div className="flex items-center space-x-4 text-xs text-muted-foreground mt-2">
              <span>Slug: {site.slug}</span>
              <span>Timezone: {site.timezone}</span>
            </div>
          </div>

          {showManagement && (hasAdminRole || hasOperatorRole) && (
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle site settings
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

function SelectedSiteDetails() {
  const [selectedSite] = useAtom(selectedSiteAtom);

  if (!selectedSite) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <MapPin className="h-5 w-5" />
          <span>{selectedSite.name}</span>
        </CardTitle>
        {selectedSite.location && (
          <CardDescription className="flex items-center">
            <MapPin className="h-4 w-4 mr-1" />
            {selectedSite.location}
          </CardDescription>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <Label className="text-muted-foreground">Slug</Label>
            <p className="font-mono text-xs">{selectedSite.slug}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Timezone</Label>
            <p>{selectedSite.timezone}</p>
          </div>
        </div>

        <Separator />

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <Label className="text-muted-foreground">Created</Label>
            <p>{new Date(selectedSite.created_at).toLocaleDateString()}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Updated</Label>
            <p>{new Date(selectedSite.updated_at).toLocaleDateString()}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}