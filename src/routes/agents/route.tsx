/**
 * route.tsx
 * /agents 路由平滑收敛与重定向中枢 (SSOT)。
 * 彻底消除过度工程，人机平权，智能体中心统一收敛收口至用户管理 (/users)。
 */
import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/agents')({
  beforeLoad: () => {
    throw redirect({
      to: '/users',
    })
  },
})
