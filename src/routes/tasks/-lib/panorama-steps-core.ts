import type { PanoramaStepDef } from './pipeline-definitions'
import { INFRA_PANORAMA_STEPS } from './panorama-steps-infra'
import { GOVERNANCE_PANORAMA_STEPS } from './panorama-steps-governance'

export { INFRA_PANORAMA_STEPS, GOVERNANCE_PANORAMA_STEPS }

export const CORE_PANORAMA_STEPS: PanoramaStepDef[] = [
  ...INFRA_PANORAMA_STEPS,
  ...GOVERNANCE_PANORAMA_STEPS,
]
