import { memo, useEffect, useState } from 'react'
import { BufferGeometry, CanvasTexture, MeshBasicMaterial, PlaneGeometry, SRGBColorSpace } from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'

type Sign = { text: string; x: number; z: number; width: number; yaw?: number; wallY?: number }

const floorSigns: Sign[] = [
  { text: 'A01 / RAF SIRASI', x: .1, z: -3.92, width: 2.65 },
  { text: 'A02 / DEPOLAMA', x: -4.12, z: .6, width: 2.65, yaw: Math.PI / 2 },
  { text: 'PALET ALANI', x: 3.25, z: 3.77, width: 1.92 },
  { text: 'K01 / ANA KORİDOR', x: -2.03, z: 3.89, width: 2.90 },
  { text: 'K02', x: 4.96, z: -2.56, width: 1.22 },
]

const doorSigns: Sign[] = [
  { text: 'YÜKLEME 01', x: 4.75, z: -5.25, width: 1.36, wallY: 2.07 },
]

export const FloorSigns = memo(function FloorSigns({ loadingDoor = false }: { loadingDoor?: boolean }) {
  const [signage, setSignage] = useState<{ geometry: BufferGeometry; material: MeshBasicMaterial }>()
  useEffect(() => {
    const signs = loadingDoor ? doorSigns : floorSigns
    const canvas = document.createElement('canvas')
    canvas.width = 512
    canvas.height = signs.length * 64
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const row = canvas.height / signs.length
    ctx.fillStyle = loadingDoor ? '#f5fbfb' : '#526466'
    ctx.font = loadingDoor ? '750 47px system-ui' : '750 38px system-ui'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const planes = signs.map(({ text, x, z, width, yaw = 0, wallY }, index) => {
      ctx.fillText(text, canvas.width / 2, row * (index + .5))
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
  }, [loadingDoor])
  return signage && <mesh name={loadingDoor ? 'loading-door-sign' : 'warehouse-signs'} {...signage} dispose={null} />
})
