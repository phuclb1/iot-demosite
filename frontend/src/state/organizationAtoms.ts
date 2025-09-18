/**
 * Organization state management using Jotai atoms.
 *
 * Manages organization data, selection, and related state for the IoT dashboard.
 * Provides reactive state for organization hierarchy and user permissions.
 */

import { atom } from 'jotai';
import { atomWithQuery } from 'jotai-tanstack-query';

// Types
export interface Organization {
  id: string;
  name: string;
  slug: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationStats {
  organization_id: string;
  site_count: number;
  area_count: number;
  device_count: number;
  online_device_count: number;
  offline_device_count: number;
}

export interface OrganizationPermissions {
  organization_id: string;
  can_view: boolean;
  can_operate: boolean;
  can_admin: boolean;
}

// Base atoms for organization state
export const selectedOrganizationIdAtom = atom<string | null>(null);
export const organizationsLoadingAtom = atom<boolean>(false);
export const organizationsErrorAtom = atom<string | null>(null);

// Query atoms for fetching organization data
export const organizationsQueryAtom = atomWithQuery(() => ({
  queryKey: ['organizations'],
  queryFn: async (): Promise<Organization[]> => {
    const response = await fetch('/api/v1/organizations', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch organizations: ${response.statusText}`);
    }

    return response.json();
  },
  staleTime: 5 * 60 * 1000, // 5 minutes
  gcTime: 10 * 60 * 1000, // 10 minutes
}));

// Selected organization query atom
export const selectedOrganizationQueryAtom = atomWithQuery((get) => {
  const selectedId = get(selectedOrganizationIdAtom);

  return {
    queryKey: ['organization', selectedId],
    queryFn: async (): Promise<Organization | null> => {
      if (!selectedId) return null;

      const response = await fetch(`/api/v1/organizations/${selectedId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch organization: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!selectedId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  };
});

// Organization statistics query atom
export const organizationStatsQueryAtom = atomWithQuery((get) => {
  const selectedId = get(selectedOrganizationIdAtom);

  return {
    queryKey: ['organization-stats', selectedId],
    queryFn: async (): Promise<OrganizationStats | null> => {
      if (!selectedId) return null;

      const response = await fetch(`/api/v1/organizations/${selectedId}/stats`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch organization stats: ${response.statusText}`);
      }

      return response.json();
    },
    enabled: !!selectedId,
    staleTime: 1 * 60 * 1000, // 1 minute for stats
    gcTime: 5 * 60 * 1000,
  };
});

// Computed atoms
export const organizationsListAtom = atom((get) => {
  const query = get(organizationsQueryAtom);
  return query.data || [];
});

export const selectedOrganizationAtom = atom((get) => {
  const query = get(selectedOrganizationQueryAtom);
  return query.data || null;
});

export const organizationStatsAtom = atom((get) => {
  const query = get(organizationStatsQueryAtom);
  return query.data || null;
});

// Organization loading states
export const organizationsIsLoadingAtom = atom((get) => {
  const organizationsQuery = get(organizationsQueryAtom);
  const selectedQuery = get(selectedOrganizationQueryAtom);
  const statsQuery = get(organizationStatsQueryAtom);

  return organizationsQuery.isLoading || selectedQuery.isLoading || statsQuery.isLoading;
});

export const organizationsHasErrorAtom = atom((get) => {
  const organizationsQuery = get(organizationsQueryAtom);
  const selectedQuery = get(selectedOrganizationQueryAtom);
  const statsQuery = get(organizationStatsQueryAtom);

  return !!(organizationsQuery.error || selectedQuery.error || statsQuery.error);
});

export const organizationsErrorMessageAtom = atom((get) => {
  const organizationsQuery = get(organizationsQueryAtom);
  const selectedQuery = get(selectedOrganizationQueryAtom);
  const statsQuery = get(organizationStatsQueryAtom);

  if (organizationsQuery.error) return organizationsQuery.error.message;
  if (selectedQuery.error) return selectedQuery.error.message;
  if (statsQuery.error) return statsQuery.error.message;

  return null;
});

// Actions atoms
export const selectOrganizationAtom = atom(
  null,
  (get, set, organizationId: string | null) => {
    set(selectedOrganizationIdAtom, organizationId);
  }
);

export const refreshOrganizationsAtom = atom(
  null,
  (get, set) => {
    // Invalidate and refetch organizations query
    const organizationsQuery = get(organizationsQueryAtom);
    organizationsQuery.refetch?.();
  }
);

export const refreshSelectedOrganizationAtom = atom(
  null,
  (get, set) => {
    // Invalidate and refetch selected organization query
    const selectedQuery = get(selectedOrganizationQueryAtom);
    const statsQuery = get(organizationStatsQueryAtom);

    selectedQuery.refetch?.();
    statsQuery.refetch?.();
  }
);

// Organization permissions atom (derived from auth state)
export const organizationPermissionsAtom = atom((get) => {
  const selectedOrg = get(selectedOrganizationAtom);

  if (!selectedOrg) return null;

  // This would typically come from the auth state
  // For now, we'll return default permissions
  return {
    organization_id: selectedOrg.id,
    can_view: true,
    can_operate: false, // This should be derived from user role and org permissions
    can_admin: false,   // This should be derived from user role
  } as OrganizationPermissions;
});

// Organization search/filter atoms
export const organizationSearchAtom = atom<string>('');
export const filteredOrganizationsAtom = atom((get) => {
  const organizations = get(organizationsListAtom);
  const search = get(organizationSearchAtom);

  if (!search.trim()) return organizations;

  const searchLower = search.toLowerCase();
  return organizations.filter(org =>
    org.name.toLowerCase().includes(searchLower) ||
    org.slug.toLowerCase().includes(searchLower) ||
    (org.description && org.description.toLowerCase().includes(searchLower))
  );
});

// Organization creation/update atoms
export const createOrganizationAtom = atom(
  null,
  async (get, set, orgData: Omit<Organization, 'id' | 'created_at' | 'updated_at'>) => {
    try {
      set(organizationsLoadingAtom, true);
      set(organizationsErrorAtom, null);

      const response = await fetch('/api/v1/organizations', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(orgData),
      });

      if (!response.ok) {
        throw new Error(`Failed to create organization: ${response.statusText}`);
      }

      const newOrganization = await response.json();

      // Refresh organizations list
      set(refreshOrganizationsAtom);

      return newOrganization;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      set(organizationsErrorAtom, errorMessage);
      throw error;
    } finally {
      set(organizationsLoadingAtom, false);
    }
  }
);

export const updateOrganizationAtom = atom(
  null,
  async (get, set, { id, ...updateData }: Partial<Organization> & { id: string }) => {
    try {
      set(organizationsLoadingAtom, true);
      set(organizationsErrorAtom, null);

      const response = await fetch(`/api/v1/organizations/${id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });

      if (!response.ok) {
        throw new Error(`Failed to update organization: ${response.statusText}`);
      }

      const updatedOrganization = await response.json();

      // Refresh organizations and selected organization if it's the one being updated
      set(refreshOrganizationsAtom);
      const selectedId = get(selectedOrganizationIdAtom);
      if (selectedId === id) {
        set(refreshSelectedOrganizationAtom);
      }

      return updatedOrganization;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      set(organizationsErrorAtom, errorMessage);
      throw error;
    } finally {
      set(organizationsLoadingAtom, false);
    }
  }
);

export const deleteOrganizationAtom = atom(
  null,
  async (get, set, organizationId: string) => {
    try {
      set(organizationsLoadingAtom, true);
      set(organizationsErrorAtom, null);

      const response = await fetch(`/api/v1/organizations/${organizationId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete organization: ${response.statusText}`);
      }

      // Clear selected organization if it was the deleted one
      const selectedId = get(selectedOrganizationIdAtom);
      if (selectedId === organizationId) {
        set(selectedOrganizationIdAtom, null);
      }

      // Refresh organizations list
      set(refreshOrganizationsAtom);

      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      set(organizationsErrorAtom, errorMessage);
      throw error;
    } finally {
      set(organizationsLoadingAtom, false);
    }
  }
);