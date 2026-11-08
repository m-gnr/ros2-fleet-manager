import { memo, useEffect, useState } from 'react'
import { BufferGeometry, CanvasTexture, MeshBasicMaterial, PlaneGeometry, SRGBColorSpace } from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'

export type Sign = { text: string; x: number; z: number; width: number; yaw?: number; wallY?: number }

const floorSigns: Sign[] = [
  { text: 'A01  /  DEPOLAMA', x: -.16, z: -4.16, width: 2.75 },
  { text: 'RAF GEÇİDİ', x: 1.40, z: -3.40, width: 1.48 },
  { text: 'ANA KORİDOR', x: -.04, z: -.87, width: 2.40, yaw: Math.PI / 2 },
  { text: 'TESLİM HAZIRLIK', x: 2.81, z: 3.47, width: 2.40 },
  { text: 'YÜKLEME', x: 4.52, z: -4.14, width: 1.48 },
  { text: 'ORTAK OPERASYON', x: -3.03, z: -2.45, width: 2.42 },
]

const doorSigns: Sign[] = [
  { text: 'GİRİŞ / YÜKLEME', x: 4.75, z: -5.25, width: 1.36, wallY: 2.07 },
]

export const FloorSigns = memo(function FloorSigns({ loadingDoor = false, custom }: { loadingDoor?: boolean; custom?: Sign[] }) {
  const [signage, setSignage] = useState<{ geometry: BufferGeometry; material: MeshBasicMaterial }>()
  useEffect(() => {
    const signs = custom ?? (loadingDoor ? doorSigns : floorSigns)
    const canvas = document.createElement('canvas')
    canvas.width = 512
    canvas.height = signs.length * 64
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const row = canvas.height / signs.length
    ctx.fillStyle = loadingDoor ? '#f5fbfb' : '#526466'
    ctx.font = loadingDoor ? '800 46px system-ui' : '800 57px system-ui'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const planes = signs.map(({ text, x, z, width, yaw = 0, wallY }, index) => {
      ctx.fillText(text, canvas.width / 2, row * (index + .5), 482)
      const plane = new PlaneGeometry(width, loadingDoor ? .24 : .42)
      const uv = plane.getAttribute('uv')
      for (let i = 0; i < uv.count; i++) uv.setY(i, (signs.length - index - 1 + uv.getY(i)) / signs.length)
      if (wallY !== undefined) return plane.translate(x, wallY, z)
      return plane.rotateX(-Math.PI / 2).rotateY(yaw).translate(x, -.011, z)
    })
    const geometry = mergeGeometries(planes)!
    for (const plane of planes) plane.dispose()
    const texture = new CanvasTexture(canvas)
    texture.colorSpace = SRGBColorSpace
    const material = new MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false })
    setSignage({ geometry, material })
    return () => {
      geometry.dispose()
      texture.dispose()
      material.dispose()
    }
  }, [loadingDoor, custom])
  return signage && <mesh name={loadingDoor ? 'loading-door-sign' : 'warehouse-signs'} {...signage} dispose={null} />
})
