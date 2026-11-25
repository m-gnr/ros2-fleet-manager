const identityColors = new Map([
  ['robot_alpha', '#2563EB'],
  ['robot_beta', '#C2410C'],
  ['robot_gamma', '#7E22CE'],
])

export function robotIdentityColor(id: string) {
  return identityColors.get(id) ?? '#475569'
}
