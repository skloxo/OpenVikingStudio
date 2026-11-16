import type { JsonSchema } from './model'

export type SchemaFormObject = Record<string, unknown>

export function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

export function resolveSchemaRef(
  schema: JsonSchema,
  rootSchema: JsonSchema,
  seen = new Set<string>(),
): JsonSchema {
  if (!schema.$ref || seen.has(schema.$ref)) return schema
  seen.add(schema.$ref)
  const ref = schema.$ref
  const match = /^#\/(\$defs|definitions)\/(.+)$/.exec(ref)
  if (!match) return schema
  const bucket = match[1] === '$defs' ? rootSchema.$defs : rootSchema.definitions
  const resolved = bucket?.[match[2]]
  if (!resolved) return schema
  const { $ref: _, ...rest } = schema
  return resolveSchemaRef({ ...resolved, ...rest }, rootSchema, seen)
}

export function normalizeSchemaNode(
  schema: JsonSchema,
  rootSchema: JsonSchema = schema,
): JsonSchema {
  const resolved = resolveSchemaRef(schema, rootSchema)
  const alternatives = resolved.anyOf || resolved.oneOf
  if (!Array.isArray(alternatives)) return resolved

  const nonNull = alternatives.filter(
    (candidate) =>
      candidate.type !== 'null' &&
      !(Array.isArray(candidate.type) && candidate.type.includes('null')),
  )
  if (nonNull.length !== 1) return resolved

  const merged: JsonSchema = {
    ...nonNull[0],
    ...resolved,
  }
  delete merged.anyOf
  delete merged.oneOf
  if (merged.default === null) delete merged.default
  return resolveSchemaRef(merged, rootSchema)
}

export function primarySchemaType(schema: JsonSchema): string | undefined {
  if (typeof schema.type === 'string') return schema.type
  if (Array.isArray(schema.type)) {
    return schema.type.find((t) => t !== 'null')
  }
  if (schema.properties) return 'object'
  if (schema.items) return 'array'
  return undefined
}

export function initialSchemaArguments(
  schema: JsonSchema,
  current: Record<string, unknown> = {},
  rootSchema: JsonSchema = schema,
): SchemaFormObject {
  const node = normalizeSchemaNode(schema, rootSchema)
  const props = node.properties || {}
  const result: SchemaFormObject = {}
  const required = new Set(node.required || [])

  for (const [key, propSchema] of Object.entries(props)) {
    const resolved = normalizeSchemaNode(propSchema, rootSchema)
    if (key in current && current[key] !== undefined) {
      if (
        primarySchemaType(resolved) === 'object' &&
        resolved.properties &&
        isPlainObject(current[key])
      ) {
        result[key] = initialSchemaArguments(
          resolved,
          current[key] as Record<string, unknown>,
          rootSchema,
        )
      } else {
        result[key] = current[key]
      }
      continue
    }
    if (resolved.default !== undefined) {
      result[key] = structuredClone(resolved.default)
    } else if (
      required.has(key) &&
      primarySchemaType(resolved) === 'object' &&
      resolved.properties
    ) {
      result[key] = initialSchemaArguments(resolved, {}, rootSchema)
    }
  }
  for (const [key, val] of Object.entries(current)) {
    if (!(key in props) && val !== undefined) result[key] = val
  }
  return result
}

export function pruneSchemaValue(
  schema: JsonSchema,
  value: unknown,
  required: boolean,
  rootSchema: JsonSchema = schema,
): unknown {
  if (value === undefined || (!required && value === null)) return undefined
  const node = normalizeSchemaNode(schema, rootSchema)
  const type = primarySchemaType(node)

  if (type === 'object' && isPlainObject(value)) {
    const reqSet = new Set(node.required || [])
    const props = node.properties || {}
    const next: Record<string, unknown> = {}
    for (const [key, child] of Object.entries(value)) {
      const childSchema = props[key]
      const cleaned = childSchema
        ? pruneSchemaValue(childSchema, child, reqSet.has(key), rootSchema)
        : child
      if (cleaned !== undefined) next[key] = cleaned
    }
    return !required && Object.keys(next).length === 0 ? undefined : next
  }

  if (type === 'array' && Array.isArray(value)) {
    const itemSchema = !Array.isArray(node.items) ? node.items : undefined
    const next = itemSchema
      ? value
          .map((item) => pruneSchemaValue(itemSchema, item, true, rootSchema))
          .filter((item) => item !== undefined)
      : value
    return !required && next.length === 0 ? undefined : next
  }

  if (!required && type === 'string' && value === '') return undefined
  return value
}

export function validateSchemaArguments(
  schema: JsonSchema,
  value: unknown,
  rootSchema: JsonSchema = schema,
  path = '',
): Record<string, string> {
  const errors: Record<string, string> = {}
  const node = normalizeSchemaNode(schema, rootSchema)
  const type = primarySchemaType(node)

  if (type === 'object') {
    const obj = isPlainObject(value) ? value : {}
    const props = node.properties || {}
    for (const reqKey of node.required || []) {
      const propPath = path ? `${path}.${reqKey}` : reqKey
      const propVal = obj[reqKey]
      const propSchema = props[reqKey]
      const propType = propSchema
        ? primarySchemaType(normalizeSchemaNode(propSchema, rootSchema))
        : undefined
      if (
        propVal === undefined ||
        propVal === null ||
        (propType === 'string' && String(propVal).trim() === '')
      ) {
        errors[propPath] = 'required'
      }
    }
    for (const [key, childSchema] of Object.entries(props)) {
      if (obj[key] === undefined || obj[key] === null) continue
      const propPath = path ? `${path}.${key}` : key
      Object.assign(
        errors,
        validateSchemaArguments(childSchema, obj[key], rootSchema, propPath),
      )
    }
    return errors
  }

  if ((type === 'number' || type === 'integer') && value !== undefined) {
    const num = Number(value)
    if (!Number.isFinite(num) || (type === 'integer' && !Number.isInteger(num))) {
      errors[path || 'root'] = 'number'
    }
  }
  return errors
}

export function prepareSchemaArguments(
  schema: JsonSchema,
  value: SchemaFormObject,
): SchemaFormObject {
  const pruned = pruneSchemaValue(schema, value, true, schema)
  return isPlainObject(pruned) ? pruned : {}
}
