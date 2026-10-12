/**
 * Schemastery configuration schema for dsh-plugin-search-gateway
 */

function Schema(def) {
  this.def = def
}

Schema.prototype.description = function(desc) {
  this.desc = desc
  return this
}

Schema.prototype.default = function(val) {
  this.defaultValue = val
  return this
}

Schema.prototype.role = function(r) {
  this.roleType = r
  return this
}

Schema.prototype.volatile = function() {
  this.isVolatile = true
  return this
}

Schema.string = function() {
  return new Schema({ type: 'string' })
}

Schema.boolean = function() {
  return new Schema({ type: 'boolean' })
}

Schema.object = function(props) {
  return new Schema({ type: 'object', properties: props })
}

export default Schema
