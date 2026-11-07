export const cameraModes = ['free', 'follow', 'top', 'fit'] as const
export type CameraMode = typeof cameraModes[number]
export type CameraCommand = { mode: CameraMode; reset: number; fit?: number }

export const cameraLabels: Record<CameraMode, string> = {
  free: 'Serbest',
  follow: 'Robotu takip et',
  top: 'Üstten',
  fit: 'Filoyu kadraja al',
}

export const warehouseOffset = [0.41, 0.77, 0.94] as const
export const startOffset = [0.76, 1.05, 0.94] as const
export const topAngle = 0.001
export const topOffset = [0, 1, Math.tan(topAngle)] as const
export const followDistance = 2.55
export const targetHeight = 0.12
export const minCameraDistance = 0.85
export const maxCameraDistance = 48

export function selectCamera(command: CameraCommand, mode: CameraMode): CameraCommand {
  if (mode === 'fit') return { ...command, mode, fit: (command.fit ?? 0) + 1 }
  return command.mode === mode ? command : { ...command, mode }
}

export function resetCamera(command: CameraCommand): CameraCommand {
  return { mode: 'free', reset: command.reset + 1 }
}

export function followTarget(x: number, z: number): [number, number, number] {
  return [x, targetHeight, z]
}
