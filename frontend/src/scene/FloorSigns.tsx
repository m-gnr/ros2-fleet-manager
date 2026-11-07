import { memo, useEffect, useState } from 'react'
import { BufferGeometry, CanvasTexture, MeshBasicMaterial, PlaneGeometry, SRGBColorSpace } from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'

const signs = [
  { text: 'A01 / RAF SIRASI', x: .1, z: -3.92, width: 2.65 },
  { text: 'A02 / DEPOLAMA', x: -4.12, z: .6, width: 2.65, yaw: Math.PI / 2 },
  { text: 'PALET ALANI', x: 3.25, z: 3.77, width: 1.92 },
  { text: 'OPERASYON KORİDORU', x: -1.85, z: 3.84, width: 3.15 },
]

export const FloorSigns = memo(function FloorSigns() {
  const [signage, setSignage] = useState<{ geometry: BufferGeometry; material: MeshBasicMaterial }>()
  useEffect(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 512
    canvas.height = 256
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const row = canvas.height / signs.length
    ctx.fillStyle = '#526466'
    ctx.font = '700 35px system-ui'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const planes = signs.map(({ text, x, z, width, yaw = 0 }, index) => {
      ctx.fillText(text, canvas.width / 2, row * (index + .5))
      const plane = new PlaneGeometry(width, .42)
      const uv = plane.getAttribute('uv')
      for (let i = 0; i < uv.count; i++) uv.setY(i, (signs.length - index - 1 + uv.getY(i)) / signs.length)
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
  }, [])
  return signage && <mesh name="warehouse-signs" {...signage} dispose={null} />
})
