export const cameraModes = ['free', 'follow', 'top', 'fit'] as const
export type CameraMode = typeof cameraModes[number]
export type CameraCommand = { mode: CameraMode; reset: number; fit?: number }

export const cameraLabels: Record<CameraMode, string> = {
  free: 'Serbest',
  follow: 'Robotu takip et',
  top: 'Üstten',
  fit: 'Filoyu kadraja al',
}

export const startOffset = [6.4, 8.5, 8.4] as const
export const targetHeight = 0.12
export const minCameraDistance = 0.85
export const maxCameraDistance = 28

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
