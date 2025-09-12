import { SetStateAction } from 'jotai'
import { 
  Organization,
  Site,
  Area,
  Device,
  TelemetryData,
  organizationsAtom,
  selectedOrganizationAtom,
  sitesAtom,
  selectedSiteAtom,
  areasAtom,
  selectedAreaAtom,
  devicesAtom,
  selectedDeviceAtom,
  telemetryDataAtom,
  realtimeTelemetryAtom,
  loadingAtom,
  errorAtom,
  timeRangeAtom,
  connectionStatusAtom,
} from './atoms'

// Type for action functions
export type AtomSetter = (update: SetStateAction<any>) => void

// Organization actions
export const setOrganizations = (set: AtomSetter) => (organizations: Organization[]) => {
  set(organizationsAtom)
  set(organizationsAtom, organizations)
}

export const selectOrganization = (set: AtomSetter) => (organization: Organization | null) => {
  set(selectedOrganizationAtom, organization)
  // Clear downstream selections
  set(selectedSiteAtom, null)
  set(selectedAreaAtom, null)
  set(selectedDeviceAtom, null)
}

// Site actions
export const setSites = (set: AtomSetter) => (sites: Site[]) => {
  set(sitesAtom, sites)
}

export const selectSite = (set: AtomSetter) => (site: Site | null) => {
  set(selectedSiteAtom, site)
  // Clear downstream selections
  set(selectedAreaAtom, null)
  set(selectedDeviceAtom, null)
}

// Area actions
export const setAreas = (set: AtomSetter) => (areas: Area[]) => {
  set(areasAtom, areas)
}

export const selectArea = (set: AtomSetter) => (area: Area | null) => {
  set(selectedAreaAtom, area)
  // Clear downstream selections
  set(selectedDeviceAtom, null)
}

// Device actions
export const setDevices = (set: AtomSetter) => (devices: Device[]) => {
  set(devicesAtom, devices)
}

export const selectDevice = (set: AtomSetter) => (device: Device | null) => {
  set(selectedDeviceAtom, device)
}

export const updateDeviceStatus = (set: AtomSetter) => (deviceId: string, status: Device['status']) => {
  set(devicesAtom, (prev: Device[]) =>
    prev.map(device =>
      device.id === deviceId
        ? { ...device, status, lastSeen: new Date() }
        : device
    )
  )
}

// Telemetry data actions
export const setTelemetryData = (set: AtomSetter) => (data: TelemetryData[]) => {
  set(telemetryDataAtom, data)
}

export const addTelemetryData = (set: AtomSetter) => (data: TelemetryData) => {
  set(telemetryDataAtom, (prev: TelemetryData[]) => [data, ...prev])
  set(realtimeTelemetryAtom, data)
}

export const clearTelemetryData = (set: AtomSetter) => () => {
  set(telemetryDataAtom, [])
  set(realtimeTelemetryAtom, null)
}

// UI state actions
export const setLoading = (set: AtomSetter) => (loading: boolean) => {
  set(loadingAtom, loading)
}

export const setError = (set: AtomSetter) => (error: string | null) => {
  set(errorAtom, error)
}

export const clearError = (set: AtomSetter) => () => {
  set(errorAtom, null)
}

// Time range actions
export const setTimeRange = (set: AtomSetter) => (start: Date, end: Date) => {
  set(timeRangeAtom, { start, end })
}

export const setLast24Hours = (set: AtomSetter) => () => {
  const end = new Date()
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000)
  set(timeRangeAtom, { start, end })
}

export const setLastWeek = (set: AtomSetter) => () => {
  const end = new Date()
  const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000)
  set(timeRangeAtom, { start, end })
}

// Connection status actions
export const setConnectionStatus = (set: AtomSetter) => (status: 'connected' | 'connecting' | 'disconnected') => {
  set(connectionStatusAtom, status)
}

// Reset all selections
export const resetSelections = (set: AtomSetter) => () => {
  set(selectedOrganizationAtom, null)
  set(selectedSiteAtom, null)
  set(selectedAreaAtom, null)
  set(selectedDeviceAtom, null)
  set(telemetryDataAtom, [])
  set(realtimeTelemetryAtom, null)
  set(errorAtom, null)
}