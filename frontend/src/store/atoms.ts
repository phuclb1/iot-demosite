import { atom } from 'jotai'

// Types for the IoT dashboard
export interface Organization {
  id: string
  name: string
}

export interface Site {
  id: string
  name: string
  organizationId: string
}

export interface Area {
  id: string
  name: string
  siteId: string
}

export interface Device {
  id: string
  name: string
  areaId: string
  status: 'online' | 'offline' | 'warning'
  lastSeen?: Date
}

export interface TelemetryData {
  deviceId: string
  timestamp: Date
  vibration: number
  temperature: number
  power: number
  electricity: number
}

// Organization atoms
export const organizationsAtom = atom<Organization[]>([])
export const selectedOrganizationAtom = atom<Organization | null>(null)

// Site atoms
export const sitesAtom = atom<Site[]>([])
export const selectedSiteAtom = atom<Site | null>(null)

// Area atoms
export const areasAtom = atom<Area[]>([])
export const selectedAreaAtom = atom<Area | null>(null)

// Device atoms
export const devicesAtom = atom<Device[]>([])
export const selectedDeviceAtom = atom<Device | null>(null)

// Telemetry data atoms
export const telemetryDataAtom = atom<TelemetryData[]>([])
export const realtimeTelemetryAtom = atom<TelemetryData | null>(null)

// UI state atoms
export const loadingAtom = atom<boolean>(false)
export const errorAtom = atom<string | null>(null)

// Time range for historical data
export const timeRangeAtom = atom<{
  start: Date
  end: Date
}>({
  start: new Date(Date.now() - 24 * 60 * 60 * 1000), // Last 24 hours
  end: new Date(),
})

// Dashboard view settings
export const dashboardViewAtom = atom<'realtime' | 'historical'>('realtime')
export const autoRefreshAtom = atom<boolean>(true)
export const refreshIntervalAtom = atom<number>(5000) // 5 seconds

// Connection status
export const connectionStatusAtom = atom<'connected' | 'connecting' | 'disconnected'>('disconnected')

// Derived atoms
export const filteredDevicesAtom = atom<Device[]>((get) => {
  const devices = get(devicesAtom)
  const selectedArea = get(selectedAreaAtom)
  
  if (!selectedArea) return devices
  
  return devices.filter(device => device.areaId === selectedArea.id)
})

export const currentTelemetryAtom = atom<TelemetryData[]>((get) => {
  const telemetryData = get(telemetryDataAtom)
  const selectedDevice = get(selectedDeviceAtom)
  
  if (!selectedDevice) return telemetryData
  
  return telemetryData.filter(data => data.deviceId === selectedDevice.id)
})

// Hierarchy breadcrumb atom
export const breadcrumbAtom = atom<string[]>((get) => {
  const selectedOrg = get(selectedOrganizationAtom)
  const selectedSite = get(selectedSiteAtom)
  const selectedArea = get(selectedAreaAtom)
  const selectedDevice = get(selectedDeviceAtom)
  
  const breadcrumb: string[] = []
  
  if (selectedOrg) breadcrumb.push(selectedOrg.name)
  if (selectedSite) breadcrumb.push(selectedSite.name)
  if (selectedArea) breadcrumb.push(selectedArea.name)
  if (selectedDevice) breadcrumb.push(selectedDevice.name)
  
  return breadcrumb
})