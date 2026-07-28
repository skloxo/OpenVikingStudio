import * as React from 'react';
import { Badge } from '#/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card';
import { cn } from '#/lib/utils';

export interface QueueItemData {
  processing: number;
  pending: number;
  completed: number;
  errors: number;
  total: number;
}

export interface QueueStatusCardProps {
  embeddingQueue?: QueueItemData;
  semanticQueue?: QueueItemData;
  semanticNodesQueue?: QueueItemData;
  isHealthy?: boolean;
}

const DEFAULT_EMBEDDING: QueueItemData = {
  processing: 0,
  pending: 0,
  completed: 989,
  errors: 0,
  total: 989,
};

const DEFAULT_SEMANTIC: QueueItemData = {
  processing: 0,
  pending: 0,
  completed: 413,
  errors: 0,
  total: 413,
};

const DEFAULT_NODES: QueueItemData = {
  processing: 0,
  pending: 0,
  completed: 0,
  errors: 0,
  total: 0,
};

function QueueRow({ title, data }: { title: string; data: QueueItemData }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium text-muted-foreground">{title}</span>
      <div className="grid grid-cols-5 gap-1.5 rounded-lg border bg-muted/20 p-1.5 text-center text-xs">
        <div className="flex flex-col items-center justify-center rounded-md bg-blue-500/10 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">处理中</span>
          <span className="font-mono text-sm font-bold text-blue-600 dark:text-blue-400 tabular-nums">
            {data.processing}
          </span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-md bg-amber-500/10 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">待处理</span>
          <span className="font-mono text-sm font-bold text-amber-600 dark:text-amber-400 tabular-nums">
            {data.pending}
          </span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-md bg-emerald-500/10 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">已完成</span>
          <span className="font-mono text-sm font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
            {data.completed}
          </span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-md bg-destructive/10 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">错误数</span>
          <span className="font-mono text-sm font-bold text-destructive tabular-nums">
            {data.errors}
          </span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-md bg-muted/50 py-1.5 px-1">
          <span className="text-[10px] text-muted-foreground">总计</span>
          <span className="font-mono text-sm font-bold text-foreground tabular-nums">
            {data.total}
          </span>
        </div>
      </div>
    </div>
  );
}

export const QueueStatusCard: React.FC<QueueStatusCardProps> = ({
  embeddingQueue = DEFAULT_EMBEDDING,
  semanticQueue = DEFAULT_SEMANTIC,
  semanticNodesQueue = DEFAULT_NODES,
  isHealthy = true,
}) => {
  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between">
        <CardTitle className="text-base font-semibold">队列状态</CardTitle>
        <Badge
          variant="outline"
          className={cn(
            'gap-1 font-normal',
            isHealthy
              ? 'border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
              : 'border-destructive/30 text-destructive'
          )}
        >
          <span
            className={cn(
              'size-1.5 rounded-full',
              isHealthy ? 'bg-emerald-500' : 'bg-destructive'
            )}
          />
          {isHealthy ? '正常' : '异常'}
        </Badge>
      </div>

      <div className="flex flex-col gap-4">
        <QueueRow title="嵌入向量队列" data={embeddingQueue} />
        <QueueRow title="语义处理队列" data={semanticQueue} />
        <QueueRow title="Semantic-Nodes" data={semanticNodesQueue} />
      </div>
    </Card>
  );
};
