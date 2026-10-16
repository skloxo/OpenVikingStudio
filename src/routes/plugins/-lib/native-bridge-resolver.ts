/**
 * native-bridge-resolver.ts
 * 客户端通信桥梁独立解析器与三渠道提示词模板引擎 (Card-150)。
 * 严格遵循第一性原理与奥卡姆剃刀，为全系 7 大插件提供独立专属桥接配置，绝不假冒混淆。
 */

export interface PluginBridgeConfig {
  pkgName: string
  version: string
  antigravityDir: string
  isLocalVault: boolean
  isExternalService: boolean
  tarballUrl: string
  installCmd: string
  dshCordisPatchYaml: string
  dshAgentPrompt: string
  antigravitySetupCmdWin: string
  antigravitySetupCmdUnix: string
  antigravityAgentPrompt: string
  universalMcpJson: string
  universalAgentPrompt: string
}

export function resolvePluginBridgeConfig(
  pluginId: string,
  pluginName: string,
  serviceAddress: string,
  effectiveApiKey: string,
  hasValidApiKey: boolean,
): PluginBridgeConfig {
  const id = (pluginId || 'openviking-memory').toLowerCase()

  // 1. Dify 独立工作流中枢
  if (id.includes('dify')) {
    const pkgName = 'dsh-plugin-dify'
    const version = '1.0.0'
    const tarballUrl = `https://vk.tide.red/studio/${pkgName}-${version}.tgz`
    const installCmd = `npm install ${tarballUrl}`
    const dshPatch = `plugins:
  '${pkgName}':
    version: '${version}'
    resolved: '${tarballUrl}'
    config:
      difyApiUrl: 'https://api.dify.ai/v1'
      apiKey: '<YOUR_DIFY_API_KEY>'`

    return {
      pkgName,
      version,
      antigravityDir: 'dify',
      isLocalVault: false,
      isExternalService: true,
      tarballUrl,
      installCmd,
      dshCordisPatchYaml: dshPatch,
      dshAgentPrompt: `请帮我安装并接入 ${pluginName} 专属 DSH 桥接器：
1. 目标插件包：${pkgName}
2. NPM 安装命令：${installCmd}
3. Dify API 端点：https://api.dify.ai/v1 (可按需调整为私有化部署地址)
4. Dify API Key：请在 Dify 控制台获取并填入
5. 请将上述配置写入 cordis.patch.yml 并重启服务。`,
      antigravitySetupCmdWin: `cmd /c mklink /J "$env:USERPROFILE\\.gemini\\config\\plugins\\dify" "OpenVikingStudio路径\\integrations\\antigravity\\dify"\npython setup.py --api https://api.dify.ai/v1 --key "<YOUR_DIFY_API_KEY>"`,
      antigravitySetupCmdUnix: `mkdir -p ~/.gemini/config/plugins && ln -s /path/to/OpenVikingStudio/integrations/antigravity/dify ~/.gemini/config/plugins/dify\ncd ~/.gemini/config/plugins/dify && python3 setup.py --api https://api.dify.ai/v1 --key "<YOUR_DIFY_API_KEY>"`,
      antigravityAgentPrompt: `请帮我将反重力座舱接入 Dify 智能体与工作流中枢：
1. 插件挂载目录：~/.gemini/config/plugins/dify/
2. Dify API 地址：https://api.dify.ai/v1
3. 专属凭据：<YOUR_DIFY_API_KEY>
4. 运行 python setup.py 完成凭据落盘并激活工作流工具。`,
      universalMcpJson: JSON.stringify(
        {
          mcpServers: {
            dify: {
              url: 'https://api.dify.ai/v1/mcp',
              headers: { Authorization: 'Bearer <YOUR_DIFY_API_KEY>' },
            },
          },
        },
        null,
        2,
      ),
      universalAgentPrompt: `请将 Dify 作为通用 MCP 工具接入当前环境：
1. 服务地址：https://api.dify.ai/v1/mcp
2. 认证头：Authorization: Bearer <YOUR_DIFY_API_KEY>
3. 写入 mcp.json 并验证工作流列表连通性。`,
    }
  }

  // 2. CPA 跨模型算力协同
  if (id.includes('cpa')) {
    const pkgName = 'dsh-plugin-cpa'
    const version = '1.0.0'
    const tarballUrl = `https://vk.tide.red/studio/${pkgName}-${version}.tgz`
    const installCmd = `npm install ${tarballUrl}`
    const dshPatch = `plugins:
  '${pkgName}':
    version: '${version}'
    resolved: '${tarballUrl}'
    config:
      endpointUrl: 'https://cpa.example.com/api'
      apiKey: '<YOUR_CPA_KEY>'`

    return {
      pkgName,
      version,
      antigravityDir: 'cpa',
      isLocalVault: false,
      isExternalService: true,
      tarballUrl,
      installCmd,
      dshCordisPatchYaml: dshPatch,
      dshAgentPrompt: `请帮我安装并接入 ${pluginName} 专属 DSH 桥接器：
1. 目标插件包：${pkgName}
2. NPM 安装命令：${installCmd}
3. 算力网关端点：https://cpa.example.com/api
4. CPA 密钥：请填入已分配的 CPA 访问凭据
5. 请将配置写入 cordis.patch.yml 并重启服务。`,
      antigravitySetupCmdWin: `cmd /c mklink /J "$env:USERPROFILE\\.gemini\\config\\plugins\\cpa" "OpenVikingStudio路径\\integrations\\antigravity\\cpa"\npython setup.py --endpoint https://cpa.example.com/api --key "<YOUR_CPA_KEY>"`,
      antigravitySetupCmdUnix: `mkdir -p ~/.gemini/config/plugins && ln -s /path/to/OpenVikingStudio/integrations/antigravity/cpa ~/.gemini/config/plugins/cpa\ncd ~/.gemini/config/plugins/cpa && python3 setup.py --endpoint https://cpa.example.com/api --key "<YOUR_CPA_KEY>"`,
      antigravityAgentPrompt: `请帮我将反重力座舱接入 CPA 算力协同插件：
1. 插件挂载目录：~/.gemini/config/plugins/cpa/
2. CPA 网关：https://cpa.example.com/api
3. 凭据：<YOUR_CPA_KEY>
4. 运行 setup.py 激活工兵扇出与专家咨询工具。`,
      universalMcpJson: JSON.stringify(
        {
          mcpServers: {
            cpa: {
              url: 'https://cpa.example.com/api/mcp',
              headers: { Authorization: 'Bearer <YOUR_CPA_KEY>' },
            },
          },
        },
        null,
        2,
      ),
      universalAgentPrompt: `请将 CPA 算力中枢接入当前客户端环境：
1. 端点：https://cpa.example.com/api/mcp
2. 认证头：Authorization: Bearer <YOUR_CPA_KEY>
3. 写入 mcp.json 并测试连通性。`,
    }
  }

  // 3. KeePass 客户端本地私有凭据中枢 (零云端依赖)
  if (id.includes('keepass')) {
    const pkgName = 'dsh-plugin-keepass-vault'
    const version = '1.0.1'
    const tarballUrl = `https://vk.tide.red/studio/${pkgName}-${version}.tgz`
    const installCmd = `npm install ${tarballUrl}`
    const dshPatch = `plugins:
  '${pkgName}':
    version: '${version}'
    resolved: '${tarballUrl}'
    config:
      kdbxPath: '~/.openviking/vault.kdbx'
      passwordEnv: 'KEEPASS_VAULT_PASSWORD'
      autoSnapshot: true`

    return {
      pkgName,
      version,
      antigravityDir: 'keepass-vault',
      isLocalVault: true,
      isExternalService: false,
      tarballUrl,
      installCmd,
      dshCordisPatchYaml: dshPatch,
      dshAgentPrompt: `请帮我安装并接入 KeePass 本地凭据保险箱插件 (零云端依赖)：
1. 目标插件包：${pkgName}
2. NPM 安装命令：${installCmd}
3. 本地 KDBX 路径：~/.openviking/vault.kdbx (或自定义本地绝对路径)
4. 主密码环境变量：KEEPASS_VAULT_PASSWORD
5. 遵循【查库第一公理】，密码 100% 留存本地，永不上云。将配置写入 cordis.patch.yml 并重启服务。`,
      antigravitySetupCmdWin: `cmd /c mklink /J "$env:USERPROFILE\\.gemini\\config\\plugins\\keepass-vault" "OpenVikingStudio路径\\integrations\\antigravity\\keepass-vault"\npython setup.py --kdbx "C:/path/to/vault.kdbx" --env KEEPASS_VAULT_PASSWORD`,
      antigravitySetupCmdUnix: `mkdir -p ~/.gemini/config/plugins && ln -s /path/to/OpenVikingStudio/integrations/antigravity/keepass-vault ~/.gemini/config/plugins/keepass-vault\ncd ~/.gemini/config/plugins/keepass-vault && python3 setup.py --kdbx ~/.openviking/vault.kdbx --env KEEPASS_VAULT_PASSWORD`,
      antigravityAgentPrompt: `请帮我将反重力座舱接入 KeePass 本地凭据保险箱：
1. 插件挂载目录：~/.gemini/config/plugins/keepass-vault/
2. 本地 KDBX 路径：~/.openviking/vault.kdbx
3. 密码环境变量：KEEPASS_VAULT_PASSWORD
4. 运行 setup.py 绑定本地数据库，外呼前自动查库，禁止明文索要密码。`,
      universalMcpJson: JSON.stringify(
        {
          mcpServers: {
            keepass: {
              command: 'python',
              args: ['-m', 'keepass_mcp_server', '--database', '~/.openviking/vault.kdbx'],
              env: { KEEPASS_PASSWORD: '<YOUR_VAULT_PASSWORD>' },
            },
          },
        },
        null,
        2,
      ),
      universalAgentPrompt: `请将 KeePass 本地凭据库作为本地 Stdio MCP 工具接入：
1. 驱动命令：python -m keepass_mcp_server --database ~/.openviking/vault.kdbx
2. 环境变量：KEEPASS_PASSWORD
3. 写入客户端 mcp.json，遵循查库第一公理。`,
    }
  }

  // 4. 原生 Ops 系统运维治理
  if (id.includes('ops')) {
    const pkgName = 'dsh-plugin-openviking-ops'
    const version = '1.0.0'
    const tarballUrl = `https://vk.tide.red/studio/${pkgName}-${version}.tgz`
    const installCmd = `npm install ${tarballUrl}`
    const dshPatch = `plugins:
  '${pkgName}':
    version: '${version}'
    resolved: '${tarballUrl}'
    config:
      endpointUrl: '${serviceAddress}'
      userKey: '${effectiveApiKey}'`

    return {
      pkgName,
      version,
      antigravityDir: 'openviking-ops',
      isLocalVault: false,
      isExternalService: false,
      tarballUrl,
      installCmd,
      dshCordisPatchYaml: dshPatch,
      dshAgentPrompt: `请帮我安装并接入 ${pluginName} 专属客户端通信桥梁：
1. 目标插件：${pkgName}
2. NPM 安装命令：${installCmd}
3. 服务地址：${serviceAddress}
4. 专属凭据：${effectiveApiKey}${!hasValidApiKey ? ' (⚠️ 请替换为在用户列表复制的真实 User Key)' : ''}
5. 请将上述配置写入 cordis.patch.yml 并重启 Harness 服务。`,
      antigravitySetupCmdWin: `cmd /c mklink /J "$env:USERPROFILE\\.gemini\\config\\plugins\\openviking-ops" "OpenVikingStudio路径\\integrations\\antigravity\\openviking-ops"\npython setup.py --api ${serviceAddress} --key "${effectiveApiKey}"`,
      antigravitySetupCmdUnix: `mkdir -p ~/.gemini/config/plugins && ln -s /path/to/OpenVikingStudio/integrations/antigravity/openviking-ops ~/.gemini/config/plugins/openviking-ops\ncd ~/.gemini/config/plugins/openviking-ops && python3 setup.py --api ${serviceAddress} --key "${effectiveApiKey}"`,
      antigravityAgentPrompt: `请帮我将反重力开发座舱接入 OpenViking 系统运维治理插件：
1. 插件挂载目录：~/.gemini/config/plugins/openviking-ops/
2. 服务端接入地址：${serviceAddress}
3. 专属授权凭据：${effectiveApiKey}
4. 运行 setup.py 激活 17 项运维特权工具与 2 项 Hook 守卫。`,
      universalMcpJson: JSON.stringify(
        {
          mcpServers: {
            openviking_ops: {
              url: `${serviceAddress}/mcp`,
              headers: {
                Authorization: `Bearer ${effectiveApiKey}`,
                'X-API-Key': effectiveApiKey,
              },
            },
          },
        },
        null,
        2,
      ),
      universalAgentPrompt: `请将 OpenViking 运维中枢接入通用 MCP 环境：
1. 端点：${serviceAddress}/mcp
2. 认证头：Authorization: Bearer ${effectiveApiKey}
3. 写入 mcp.json 并验证运维特权连通性。`,
    }
  }

  // 5. 原生 Fleet 卫星同频
  if (id.includes('fleet')) {
    const pkgName = 'dsh-plugin-openviking-fleet'
    const version = '1.0.0'
    const tarballUrl = `https://vk.tide.red/studio/${pkgName}-${version}.tgz`
    const installCmd = `npm install ${tarballUrl}`
    const dshPatch = `plugins:
  '${pkgName}':
    version: '${version}'
    resolved: '${tarballUrl}'
    config:
      endpointUrl: '${serviceAddress}'
      userKey: '${effectiveApiKey}'`

    return {
      pkgName,
      version,
      antigravityDir: 'openviking-fleet',
      isLocalVault: false,
      isExternalService: false,
      tarballUrl,
      installCmd,
      dshCordisPatchYaml: dshPatch,
      dshAgentPrompt: `请帮我安装并接入 ${pluginName} 专属客户端通信桥梁：
1. 目标插件：${pkgName}
2. NPM 安装命令：${installCmd}
3. 服务地址：${serviceAddress}
4. 专属凭据：${effectiveApiKey}${!hasValidApiKey ? ' (⚠️ 请替换为在用户列表复制的真实 User Key)' : ''}
5. 请将上述配置写入 cordis.patch.yml 并重启 Harness 服务。`,
      antigravitySetupCmdWin: `cmd /c mklink /J "$env:USERPROFILE\\.gemini\\config\\plugins\\openviking-fleet" "OpenVikingStudio路径\\integrations\\antigravity\\openviking-fleet"\npython setup.py --api ${serviceAddress} --key "${effectiveApiKey}"`,
      antigravitySetupCmdUnix: `mkdir -p ~/.gemini/config/plugins && ln -s /path/to/OpenVikingStudio/integrations/antigravity/openviking-fleet ~/.gemini/config/plugins/openviking-fleet\ncd ~/.gemini/config/plugins/openviking-fleet && python3 setup.py --api ${serviceAddress} --key "${effectiveApiKey}"`,
      antigravityAgentPrompt: `请帮我将反重力开发座舱接入卫星集群同频运维插件：
1. 插件挂载目录：~/.gemini/config/plugins/openviking-fleet/
2. 服务端接入地址：${serviceAddress}
3. 专属授权凭据：${effectiveApiKey}
4. 运行 setup.py 激活集群体检与一键同频工具。`,
      universalMcpJson: JSON.stringify(
        {
          mcpServers: {
            openviking_fleet: {
              url: `${serviceAddress}/mcp`,
              headers: {
                Authorization: `Bearer ${effectiveApiKey}`,
                'X-API-Key': effectiveApiKey,
              },
            },
          },
        },
        null,
        2,
      ),
      universalAgentPrompt: `请将 OpenViking 卫星集群同频接入通用 MCP：
1. 端点：${serviceAddress}/mcp
2. 认证头：Authorization: Bearer ${effectiveApiKey}
3. 写入 mcp.json 并测试集群体检工具。`,
    }
  }

  // 6. 原生 Memory 核心长程记忆与代码战地 (默认)
  const pkgName = 'dsh-plugin-openviking-memory'
  const version = '2.0.12'
  const tarballUrl = `https://vk.tide.red/studio/${pkgName}-${version}.tgz`
  const installCmd = `npm install ${tarballUrl}`
  const dshPatch = `plugins:
  '${pkgName}':
    version: '${version}'
    resolved: '${tarballUrl}'
    config:
      endpointUrl: '${serviceAddress}'
      userKey: '${effectiveApiKey}'`

  return {
    pkgName,
    version,
    antigravityDir: 'openviking-memory',
    isLocalVault: false,
    isExternalService: false,
    tarballUrl,
    installCmd,
    dshCordisPatchYaml: dshPatch,
    dshAgentPrompt: `请帮我安装并接入 ${pluginName} 专属客户端通信桥梁：
1. 目标插件：${pkgName}
2. NPM 安装命令：${installCmd}
3. 服务地址：${serviceAddress}
4. 专属凭据：${effectiveApiKey}${!hasValidApiKey ? ' (⚠️ 请替换为在用户列表复制的真实 User Key)' : ''}
5. 请将上述配置写入 cordis.patch.yml 并重启 Harness 服务。`,
    antigravitySetupCmdWin: `cmd /c mklink /J "$env:USERPROFILE\\.gemini\\config\\plugins\\openviking-memory" "OpenVikingStudio路径\\integrations\\antigravity\\openviking-memory"\npython setup.py --api ${serviceAddress} --key "${effectiveApiKey}"`,
    antigravitySetupCmdUnix: `mkdir -p ~/.gemini/config/plugins && ln -s /path/to/OpenVikingStudio/integrations/antigravity/openviking-memory ~/.gemini/config/plugins/openviking-memory\ncd ~/.gemini/config/plugins/openviking-memory && python3 setup.py --api ${serviceAddress} --key "${effectiveApiKey}"`,
    antigravityAgentPrompt: `请帮我将当前反重力开发座舱 (Antigravity IDE) 接入 OpenViking 核心战地长程记忆：
1. 插件挂载规范目录：~/.gemini/config/plugins/openviking-memory/
2. 服务端接入地址：${serviceAddress}
3. 专属授权凭据：${effectiveApiKey}${!hasValidApiKey ? ' (⚠️ 请替换为在用户列表复制的真实 User Key)' : ''}
4. 执行要求：
   - 将插件源码通过目录软链挂载至全局 plugins 目录；
   - 运行 python setup.py --api ${serviceAddress} --key "${effectiveApiKey}" 完成凭据落盘；
   - 激活 PreInvocation（记忆预取）、PreToolUse（沙箱守卫）与 Stop（会话归档）三大完整 Hook。`,
    universalMcpJson: JSON.stringify(
      {
        mcpServers: {
          openviking: {
            url: `${serviceAddress}/mcp`,
            headers: {
              Authorization: `Bearer ${effectiveApiKey}`,
              'X-API-Key': effectiveApiKey,
            },
          },
        },
      },
      null,
      2,
    ),
    universalAgentPrompt: `请帮我将 OpenViking 体外大脑作为通用 MCP 工具接入当前环境：
1. MCP 服务协议端点：${serviceAddress}/mcp (Streamable HTTP 模式)
2. 认证请求头：Authorization: Bearer ${effectiveApiKey}${!hasValidApiKey ? ' (⚠️ 请替换为在用户列表复制的真实 User Key)' : ''}
3. 请写入 mcp.json 并验证连通性。`,
  }
}
