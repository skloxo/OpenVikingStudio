/**
 * Stanford DSPy (MIPO) 强类型提示词编译器前端类型定义 (SSOT)
 */

export interface DSPyFieldContract {
  name: string;
  field_type: string;
  description: string;
  required: boolean;
}

export interface CompiledSignature {
  name: string;
  task_objective: string;
  input_fields: DSPyFieldContract[];
  output_fields: DSPyFieldContract[];
  constraints: string[];
}

export interface BootstrapExample {
  example_id: string;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  quality_score: number;
  verified: boolean;
  source: string;
}

export interface DSPyCompileRequest {
  raw_prompt: string;
  signature_name?: string;
  task_objective?: string;
  candidate_examples?: BootstrapExample[];
  max_few_shot?: number;
  strict_typing?: boolean;
  anti_hallucination_gate?: boolean;
}

export interface DSPyCompileResult {
  compiled_prompt: string;
  signature: CompiledSignature;
  selected_few_shot: BootstrapExample[];
  original_token_count: number;
  compiled_token_count: number;
  compression_ratio: number;
  contract_status: "PASS" | "PARTIAL" | "FAIL";
  anti_hallucination_injected: boolean;
  elapsed_ms: number;
}

export interface DSPyCompilerStats {
  total_compilations: number;
  total_original_tokens: number;
  total_compiled_tokens: number;
  average_latency_ms: number;
  pass_contract_count: number;
}
