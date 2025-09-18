/**
 * Organization selector component using React, Shadcn UI, and Jotai state management.
 *
 * Provides organization selection interface with search, filtering,
 * and organization management capabilities.
 */

'use client';

import React, { useState } from 'react';
import { useAtom } from 'jotai';
import { Check, ChevronsUpDown, Building2, Search, Plus, Settings, Users, BarChart3 } from 'lucide-react';

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
  organizationsListAtom,
  selectedOrganizationIdAtom,
  selectedOrganizationAtom,
  organizationStatsAtom,
  selectOrganizationAtom,
  organizationsIsLoadingAtom,
  organizationsHasErrorAtom,
  organizationsErrorMessageAtom,
  filteredOrganizationsAtom,
  organizationSearchAtom,
  refreshOrganizationsAtom,
} from '@/state/organizationAtoms';

import { hasAdminRoleAtom, hasOperatorRoleAtom, userAtom } from '@/state/authAtoms';

interface OrganizationSelectorProps {
  className?: string;
  showStats?: boolean;
  showSearch?: boolean;
  showManagement?: boolean;
  variant?: 'default' | 'compact' | 'card';
}

export default function OrganizationSelector({
  className = '',
  showStats = true,
  showSearch = true,
  showManagement = false,
  variant = 'default'
}: OrganizationSelectorProps) {
  // State atoms
  const [organizations] = useAtom(organizationsListAtom);
  const [selectedOrgId] = useAtom(selectedOrganizationIdAtom);
  const [selectedOrg] = useAtom(selectedOrganizationAtom);
  const [orgStats] = useAtom(organizationStatsAtom);
  const [, selectOrganization] = useAtom(selectOrganizationAtom);
  const [isLoading] = useAtom(organizationsIsLoadingAtom);
  const [hasError] = useAtom(organizationsHasErrorAtom);
  const [errorMessage] = useAtom(organizationsErrorMessageAtom);
  const [filteredOrgs] = useAtom(filteredOrganizationsAtom);
  const [searchQuery, setSearchQuery] = useAtom(organizationSearchAtom);
  const [, refreshOrganizations] = useAtom(refreshOrganizationsAtom);

  // Permission atoms
  const [hasAdminRole] = useAtom(hasAdminRoleAtom);
  const [hasOperatorRole] = useAtom(hasOperatorRoleAtom);
  const [user] = useAtom(userAtom);

  // Local state
  const [open, setOpen] = useState(false);

  const handleSelect = (orgId: string) => {
    selectOrganization(orgId === selectedOrgId ? null : orgId);
    setOpen(false);
  };

  const handleRefresh = () => {
    refreshOrganizations();
  };

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
              disabled={isLoading}
            >
              {selectedOrg ? (
                <span className="truncate">{selectedOrg.name}</span>
              ) : (
                "Select organization..."
              )}
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[200px] p-0">
            <Command>
              <CommandInput placeholder="Search organizations..." />
              <CommandEmpty>No organization found.</CommandEmpty>
              <CommandGroup>
                {organizations.map((org) => (
                  <CommandItem
                    key={org.id}
                    value={org.id}
                    onSelect={handleSelect}
                  >
                    <Check
                      className={`mr-2 h-4 w-4 ${
                        selectedOrgId === org.id ? "opacity-100" : "opacity-0"
                      }`}
                    />
                    <div className="flex flex-col">
                      <span>{org.name}</span>
                      {org.description && (
                        <span className="text-xs text-muted-foreground truncate">
                          {org.description}
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
            <Building2 className="h-5 w-5" />
            <span>Organization</span>
          </CardTitle>
          {selectedOrg && (
            <CardDescription>
              {selectedOrg.description || 'No description available'}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <OrganizationSelector variant="compact" />
          {showStats && selectedOrg && orgStats && (
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold">{orgStats.site_count}</p>
                <p className="text-sm text-muted-foreground">Sites</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold">{orgStats.device_count}</p>
                <p className="text-sm text-muted-foreground">Devices</p>
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
          <Building2 className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Organizations</h3>
          {organizations.length > 0 && (
            <Badge variant="secondary">{organizations.length}</Badge>
          )}
        </div>

        {showManagement && hasAdminRole && (
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isLoading}
            >
              Refresh
            </Button>
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Organization
            </Button>
          </div>
        )}
      </div>

      {/* Search */}
      {showSearch && organizations.length > 5 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search organizations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      )}

      {/* Error state */}
      {hasError && (
        <Alert variant="destructive">
          <AlertDescription>{errorMessage}</AlertDescription>
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

      {/* Organization list */}
      {!isLoading && !hasError && (
        <div className="space-y-2">
          {filteredOrgs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery ? 'No organizations found matching your search.' : 'No organizations available.'}
            </div>
          ) : (
            filteredOrgs.map((org) => (
              <OrganizationCard
                key={org.id}
                organization={org}
                isSelected={selectedOrgId === org.id}
                onSelect={handleSelect}
                showStats={showStats}
                showManagement={showManagement}
              />
            ))
          )}
        </div>
      )}

      {/* Selected organization details */}
      {selectedOrg && showStats && (
        <SelectedOrganizationDetails />
      )}
    </div>
  );
}

interface OrganizationCardProps {
  organization: any;
  isSelected: boolean;
  onSelect: (orgId: string) => void;
  showStats: boolean;
  showManagement: boolean;
}

function OrganizationCard({
  organization,
  isSelected,
  onSelect,
  showStats,
  showManagement
}: OrganizationCardProps) {
  const [hasAdminRole] = useAtom(hasAdminRoleAtom);
  const [hasOperatorRole] = useAtom(hasOperatorRoleAtom);

  return (
    <Card
      className={`cursor-pointer transition-colors ${
        isSelected ? 'ring-2 ring-primary bg-primary/5' : 'hover:bg-muted/50'
      }`}
      onClick={() => onSelect(organization.id)}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h4 className="font-medium">{organization.name}</h4>
              {isSelected && (
                <Badge variant="default" className="text-xs">
                  Selected
                </Badge>
              )}
            </div>
            {organization.description && (
              <p className="text-sm text-muted-foreground mt-1">
                {organization.description}
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Slug: {organization.slug}
            </p>
          </div>

          {showManagement && (hasAdminRole || hasOperatorRole) && (
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle organization settings
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

function SelectedOrganizationDetails() {
  const [selectedOrg] = useAtom(selectedOrganizationAtom);
  const [orgStats] = useAtom(organizationStatsAtom);

  if (!selectedOrg) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Building2 className="h-5 w-5" />
          <span>{selectedOrg.name}</span>
        </CardTitle>
        {selectedOrg.description && (
          <CardDescription>{selectedOrg.description}</CardDescription>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
              <Building2 className="h-4 w-4" />
              <span>Sites</span>
            </div>
            <p className="text-2xl font-bold">
              {orgStats?.site_count || 0}
            </p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
              <BarChart3 className="h-4 w-4" />
              <span>Areas</span>
            </div>
            <p className="text-2xl font-bold">
              {orgStats?.area_count || 0}
            </p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
              <Users className="h-4 w-4" />
              <span>Devices</span>
            </div>
            <p className="text-2xl font-bold">
              {orgStats?.device_count || 0}
            </p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
              <div className="h-2 w-2 bg-green-500 rounded-full"></div>
              <span>Online</span>
            </div>
            <p className="text-2xl font-bold text-green-600">
              {orgStats?.online_device_count || 0}
            </p>
          </div>
        </div>

        {orgStats && orgStats.device_count > 0 && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Device Status</span>
              <span>
                {Math.round((orgStats.online_device_count / orgStats.device_count) * 100)}% Online
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-500 h-2 rounded-full"
                style={{
                  width: `${(orgStats.online_device_count / orgStats.device_count) * 100}%`
                }}
              ></div>
            </div>
          </div>
        )}

        <Separator />

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <Label className="text-muted-foreground">Created</Label>
            <p>{new Date(selectedOrg.created_at).toLocaleDateString()}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Updated</Label>
            <p>{new Date(selectedOrg.updated_at).toLocaleDateString()}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}