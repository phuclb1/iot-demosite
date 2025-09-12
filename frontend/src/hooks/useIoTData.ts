import { useCallback } from 'react'
import { useAtom, useSetAtom } from 'jotai'
import {
  organizationsAtom,
  selectedOrganizationAtom,
  sitesAtom,
  selectedSiteAtom,
  areasAtom,
  selectedAreaAtom,
  devicesAtom,
  selectedDeviceAtom,
  telemetryDataAtom,
  loadingAtom,
  errorAtom,
  timeRangeAtom,
  connectionStatusAtom,
} from '@/store/atoms'

// Custom hook for managing IoT dashboard data
export function useIoTData() {
  // Atoms
  const [organizations] = useAtom(organizationsAtom)
  const [selectedOrganization, setSelectedOrganization] = useAtom(selectedOrganizationAtom)
  const [sites] = useAtom(sitesAtom)
  const [selectedSite, setSelectedSite] = useAtom(selectedSiteAtom)
  const [areas] = useAtom(areasAtom)
  const [selectedArea, setSelectedArea] = useAtom(selectedAreaAtom)
  const [devices] = useAtom(devicesAtom)
  const [selectedDevice, setSelectedDevice] = useAtom(selectedDeviceAtom)
  const [telemetryData] = useAtom(telemetryDataAtom)
  const [loading, setLoading] = useAtom(loadingAtom)
  const [error, setError] = useAtom(errorAtom)
  const [timeRange] = useAtom(timeRangeAtom)
  const [connectionStatus] = useAtom(connectionStatusAtom)

  // Setters
  const setOrganizations = useSetAtom(organizationsAtom)
  const setSites = useSetAtom(sitesAtom)
  const setAreas = useSetAtom(areasAtom)
  const setDevices = useSetAtom(devicesAtom)
  const setTelemetryData = useSetAtom(telemetryDataAtom)
  const setConnectionStatus = useSetAtom(connectionStatusAtom)

  // API calls
  const fetchOrganizations = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch('/api/v1/organizations')
      if (!response.ok) throw new Error('Failed to fetch organizations')
      
      const data = await response.json()
      setOrganizations(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch organizations')
    } finally {
      setLoading(false)
    }
  }, [setLoading, setError, setOrganizations])

  const fetchSites = useCallback(async (orgId: string) => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`/api/v1/organizations/${orgId}/sites`)
      if (!response.ok) throw new Error('Failed to fetch sites')
      
      const data = await response.json()
      setSites(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch sites')
    } finally {
      setLoading(false)
    }
  }, [setLoading, setError, setSites])

  const fetchAreas = useCallback(async (orgId: string, siteId: string) => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`/api/v1/organizations/${orgId}/sites/${siteId}/areas`)
      if (!response.ok) throw new Error('Failed to fetch areas')
      
      const data = await response.json()
      setAreas(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch areas')
    } finally {
      setLoading(false)
    }
  }, [setLoading, setError, setAreas])

  const fetchDevices = useCallback(async (orgId: string, siteId: string, areaId: string) => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`/api/v1/organizations/${orgId}/sites/${siteId}/areas/${areaId}/devices`)
      if (!response.ok) throw new Error('Failed to fetch devices')
      
      const data = await response.json()
      setDevices(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch devices')
    } finally {
      setLoading(false)
    }
  }, [setLoading, setError, setDevices])

  const fetchCurrentTelemetry = useCallback(async (deviceId: string) => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`/api/v1/telemetry/current/${deviceId}`)
      if (!response.ok) throw new Error('Failed to fetch current telemetry')
      
      const data = await response.json()
      if (data) {
        setTelemetryData([data])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch current telemetry')
    } finally {
      setLoading(false)
    }
  }, [setLoading, setError, setTelemetryData])

  const fetchHistoricalTelemetry = useCallback(async (deviceId: string, start: Date, end: Date) => {
    try {
      setLoading(true)
      setError(null)
      
      const params = new URLSearchParams({
        start: start.toISOString(),
        end: end.toISOString(),
      })
      
      const response = await fetch(`/api/v1/telemetry/historical/${deviceId}?${params}`)
      if (!response.ok) throw new Error('Failed to fetch historical telemetry')
      
      const data = await response.json()
      setTelemetryData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch historical telemetry')
    } finally {
      setLoading(false)
    }
  }, [setLoading, setError, setTelemetryData])

  // Selection handlers with cascade clearing
  const handleSelectOrganization = useCallback((org: typeof selectedOrganization) => {
    setSelectedOrganization(org)
    setSelectedSite(null)
    setSelectedArea(null)
    setSelectedDevice(null)
    setSites([])
    setAreas([])
    setDevices([])
    setTelemetryData([])
  }, [setSelectedOrganization, setSelectedSite, setSelectedArea, setSelectedDevice, setSites, setAreas, setDevices, setTelemetryData])

  const handleSelectSite = useCallback((site: typeof selectedSite) => {
    setSelectedSite(site)
    setSelectedArea(null)
    setSelectedDevice(null)
    setAreas([])
    setDevices([])
    setTelemetryData([])
  }, [setSelectedSite, setSelectedArea, setSelectedDevice, setAreas, setDevices, setTelemetryData])

  const handleSelectArea = useCallback((area: typeof selectedArea) => {
    setSelectedArea(area)
    setSelectedDevice(null)
    setDevices([])
    setTelemetryData([])
  }, [setSelectedArea, setSelectedDevice, setDevices, setTelemetryData])

  const handleSelectDevice = useCallback((device: typeof selectedDevice) => {
    setSelectedDevice(device)
    setTelemetryData([])
  }, [setSelectedDevice, setTelemetryData])

  return {
    // State
    organizations,
    selectedOrganization,
    sites,
    selectedSite,
    areas,
    selectedArea,
    devices,
    selectedDevice,
    telemetryData,
    loading,
    error,
    timeRange,
    connectionStatus,

    // Actions
    fetchOrganizations,
    fetchSites,
    fetchAreas,
    fetchDevices,
    fetchCurrentTelemetry,
    fetchHistoricalTelemetry,

    // Selection handlers
    handleSelectOrganization,
    handleSelectSite,
    handleSelectArea,
    handleSelectDevice,

    // Direct setters
    setConnectionStatus,
    setError,
  }
}