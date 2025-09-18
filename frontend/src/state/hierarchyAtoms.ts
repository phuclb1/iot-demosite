/**
 * Device hierarchy state management using Jotai atoms.
 *
 * Manages the hierarchical structure (Organization → Site → Area → Device)
 * and provides reactive state for navigation and selection.
 */

import { atom } from 'jotai';
import { atomWithQuery } from 'jotai-tanstack-query';
import { selectedOrganizationIdAtom } from './organizationAtoms';

// Types
export interface Site {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  location?: string;
  timezone: string;
  created_at: string;
  updated_at: string;
}

export interface Area {
  id: string;
  site_id: string;
  name: string;
  slug: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface Device {
  id: string;
  area_id: string;
  name: string;
  model: string;
  firmware_version?: string;
  mac_address?: string;
  last_seen?: string;
  status: 'online' | 'offline' | 'maintenance';
  created_at: string;
  updated_at: string;
}

export interface DeviceStats {
  area_id: string;
  device_count: number;
  online_device_count: number;
  offline_device_count: number;
  maintenance_device_count: number;
}

export interface HierarchyPath {
  organization?: { id: string; name: string };
  site?: { id: string; name: string };
  area?: { id: string; name: string };
  device?: { id: string; name: string };
}

// Base selection atoms
export const selectedSiteIdAtom = atom<string | null>(null);
export const selectedAreaIdAtom = atom<string | null>(null);
export const selectedDeviceIdAtom = atom<string | null>(null);

// Loading and error atoms
export const hierarchyLoadingAtom = atom<boolean>(false);
export const hierarchyErrorAtom = atom<string | null>(null);

// Sites query atom
export const sitesQueryAtom = atomWithQuery((get) => {
  const organizationId = get(selectedOrganizationIdAtom);

  return {
    queryKey: ['sites', organizationId],
    queryFn: async (): Promise<Site[]> => {
      if (!organizationId) return [];

      const response = await fetch(`/api/v1/organizations/${organizationId}/sites`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch sites: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!organizationId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,
  };
});

// Areas query atom
export const areasQueryAtom = atomWithQuery((get) => {
  const organizationId = get(selectedOrganizationIdAtom);
  const siteId = get(selectedSiteIdAtom);

  return {
    queryKey: ['areas', organizationId, siteId],
    queryFn: async (): Promise<Area[]> => {
      if (!organizationId || !siteId) return [];

      const response = await fetch(
        `/api/v1/organizations/${organizationId}/sites/${siteId}/areas`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch areas: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!organizationId && !!siteId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  };
});

// Devices query atom
export const devicesQueryAtom = atomWithQuery((get) => {
  const organizationId = get(selectedOrganizationIdAtom);
  const siteId = get(selectedSiteIdAtom);
  const areaId = get(selectedAreaIdAtom);

  return {
    queryKey: ['devices', organizationId, siteId, areaId],
    queryFn: async (): Promise<Device[]> => {
      if (!organizationId || !siteId || !areaId) return [];

      const response = await fetch(
        `/api/v1/organizations/${organizationId}/sites/${siteId}/areas/${areaId}/devices`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch devices: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!organizationId && !!siteId && !!areaId,
    staleTime: 2 * 60 * 1000, // 2 minutes for devices (more dynamic)
    gcTime: 5 * 60 * 1000,
  };
});

// Selected entities query atoms
export const selectedSiteQueryAtom = atomWithQuery((get) => {
  const organizationId = get(selectedOrganizationIdAtom);
  const siteId = get(selectedSiteIdAtom);

  return {
    queryKey: ['site', organizationId, siteId],
    queryFn: async (): Promise<Site | null> => {
      if (!organizationId || !siteId) return null;

      const response = await fetch(
        `/api/v1/organizations/${organizationId}/sites/${siteId}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch site: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!organizationId && !!siteId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  };
});

export const selectedAreaQueryAtom = atomWithQuery((get) => {
  const organizationId = get(selectedOrganizationIdAtom);
  const siteId = get(selectedSiteIdAtom);
  const areaId = get(selectedAreaIdAtom);

  return {
    queryKey: ['area', organizationId, siteId, areaId],
    queryFn: async (): Promise<Area | null> => {
      if (!organizationId || !siteId || !areaId) return null;

      const response = await fetch(
        `/api/v1/organizations/${organizationId}/sites/${siteId}/areas/${areaId}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch area: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!organizationId && !!siteId && !!areaId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  };
});

export const selectedDeviceQueryAtom = atomWithQuery((get) => {
  const organizationId = get(selectedOrganizationIdAtom);
  const siteId = get(selectedSiteIdAtom);
  const areaId = get(selectedAreaIdAtom);
  const deviceId = get(selectedDeviceIdAtom);

  return {
    queryKey: ['device', organizationId, siteId, areaId, deviceId],
    queryFn: async (): Promise<Device | null> => {
      if (!organizationId || !siteId || !areaId || !deviceId) return null;

      const response = await fetch(
        `/api/v1/organizations/${organizationId}/sites/${siteId}/areas/${areaId}/devices/${deviceId}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch device: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!organizationId && !!siteId && !!areaId && !!deviceId,
    staleTime: 1 * 60 * 1000, // 1 minute for device details
    gcTime: 5 * 60 * 1000,
  };
});

// Computed atoms
export const sitesListAtom = atom((get) => {
  const query = get(sitesQueryAtom);
  return query.data || [];
});

export const areasListAtom = atom((get) => {
  const query = get(areasQueryAtom);
  return query.data || [];
});

export const devicesListAtom = atom((get) => {
  const query = get(devicesQueryAtom);
  return query.data || [];
});

export const selectedSiteAtom = atom((get) => {
  const query = get(selectedSiteQueryAtom);
  return query.data || null;
});

export const selectedAreaAtom = atom((get) => {
  const query = get(selectedAreaQueryAtom);
  return query.data || null;
});

export const selectedDeviceAtom = atom((get) => {
  const query = get(selectedDeviceQueryAtom);
  return query.data || null;
});

// Loading states
export const hierarchyIsLoadingAtom = atom((get) => {
  const sitesQuery = get(sitesQueryAtom);
  const areasQuery = get(areasQueryAtom);
  const devicesQuery = get(devicesQueryAtom);

  return sitesQuery.isLoading || areasQuery.isLoading || devicesQuery.isLoading;
});

export const hierarchyHasErrorAtom = atom((get) => {
  const sitesQuery = get(sitesQueryAtom);
  const areasQuery = get(areasQueryAtom);
  const devicesQuery = get(devicesQueryAtom);

  return !!(sitesQuery.error || areasQuery.error || devicesQuery.error);
});

// Current hierarchy path atom
export const currentHierarchyPathAtom = atom((get) => {
  const organizationQuery = get(selectedOrganizationIdAtom);
  const siteQuery = get(selectedSiteQueryAtom);
  const areaQuery = get(selectedAreaQueryAtom);
  const deviceQuery = get(selectedDeviceQueryAtom);

  const path: HierarchyPath = {};

  if (organizationQuery) {
    path.organization = { id: organizationQuery, name: '' }; // Name would come from org atom
  }

  if (siteQuery.data) {
    path.site = { id: siteQuery.data.id, name: siteQuery.data.name };
  }

  if (areaQuery.data) {
    path.area = { id: areaQuery.data.id, name: areaQuery.data.name };
  }

  if (deviceQuery.data) {
    path.device = { id: deviceQuery.data.id, name: deviceQuery.data.name };
  }

  return path;
});

// Device filtering atoms
export const deviceStatusFilterAtom = atom<'all' | 'online' | 'offline' | 'maintenance'>('all');
export const deviceSearchAtom = atom<string>('');

export const filteredDevicesAtom = atom((get) => {
  const devices = get(devicesListAtom);
  const statusFilter = get(deviceStatusFilterAtom);
  const search = get(deviceSearchAtom);

  let filtered = devices;

  // Apply status filter
  if (statusFilter !== 'all') {
    filtered = filtered.filter(device => device.status === statusFilter);
  }

  // Apply search filter
  if (search.trim()) {
    const searchLower = search.toLowerCase();
    filtered = filtered.filter(device =>
      device.name.toLowerCase().includes(searchLower) ||
      device.model.toLowerCase().includes(searchLower) ||
      (device.mac_address && device.mac_address.toLowerCase().includes(searchLower))
    );
  }

  return filtered;
});

// Device statistics atom
export const deviceStatsAtom = atom((get) => {
  const devices = get(devicesListAtom);

  const stats = {
    total: devices.length,
    online: devices.filter(d => d.status === 'online').length,
    offline: devices.filter(d => d.status === 'offline').length,
    maintenance: devices.filter(d => d.status === 'maintenance').length,
  };

  return {
    ...stats,
    onlinePercentage: stats.total > 0 ? Math.round((stats.online / stats.total) * 100) : 0,
  };
});

// Selection action atoms
export const selectSiteAtom = atom(
  null,
  (get, set, siteId: string | null) => {
    set(selectedSiteIdAtom, siteId);
    // Clear downstream selections
    set(selectedAreaIdAtom, null);
    set(selectedDeviceIdAtom, null);
  }
);

export const selectAreaAtom = atom(
  null,
  (get, set, areaId: string | null) => {
    set(selectedAreaIdAtom, areaId);
    // Clear downstream selections
    set(selectedDeviceIdAtom, null);
  }
);

export const selectDeviceAtom = atom(
  null,
  (get, set, deviceId: string | null) => {
    set(selectedDeviceIdAtom, deviceId);
  }
);

// Navigation action atoms
export const navigateToSiteAtom = atom(
  null,
  (get, set, siteId: string) => {
    set(selectSiteAtom, siteId);
  }
);

export const navigateToAreaAtom = atom(
  null,
  (get, set, { siteId, areaId }: { siteId: string; areaId: string }) => {
    set(selectSiteAtom, siteId);
    set(selectAreaAtom, areaId);
  }
);

export const navigateToDeviceAtom = atom(
  null,
  (get, set, { siteId, areaId, deviceId }: { siteId: string; areaId: string; deviceId: string }) => {
    set(selectSiteAtom, siteId);
    set(selectAreaAtom, areaId);
    set(selectDeviceAtom, deviceId);
  }
);

// Reset hierarchy selection
export const resetHierarchySelectionAtom = atom(
  null,
  (get, set) => {
    set(selectedSiteIdAtom, null);
    set(selectedAreaIdAtom, null);
    set(selectedDeviceIdAtom, null);
  }
);

// Refresh action atoms
export const refreshSitesAtom = atom(
  null,
  (get, set) => {
    const sitesQuery = get(sitesQueryAtom);
    sitesQuery.refetch?.();
  }
);

export const refreshAreasAtom = atom(
  null,
  (get, set) => {
    const areasQuery = get(areasQueryAtom);
    areasQuery.refetch?.();
  }
);

export const refreshDevicesAtom = atom(
  null,
  (get, set) => {
    const devicesQuery = get(devicesQueryAtom);
    devicesQuery.refetch?.();
  }
);

export const refreshHierarchyAtom = atom(
  null,
  (get, set) => {
    set(refreshSitesAtom);
    set(refreshAreasAtom);
    set(refreshDevicesAtom);
  }
);