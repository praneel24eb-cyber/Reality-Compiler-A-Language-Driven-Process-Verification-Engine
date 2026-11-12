import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  type Node, type Edge, type NodeTypes, type EdgeTypes,
  MarkerType, Handle, Position, BaseEdge, getSmoothStepPath,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import clsx from 'clsx';
import type { Process, State, Transition } from '@/lib/types';

// ── Custom Node ──
function WorkflowNode({ data }: { data: { state: State; selected?: boolean } }) {
  const s = data.state;
  const border = s.kind === 'start' ? 'border-l-green-400' : s.kind === 'terminal' ? 'border-l-teal-400' : 'border-l-surface-400';
  const badge = s.kind === 'start' ? 'bg-green-50 text-green-700' : s.kind === 'terminal' ? 'bg-teal-50 text-teal-700' : 'bg-gray-100 text-gray-500';
  return (
    <div className={clsx(
      'bg-white rounded-xl border border-surface-300 shadow-card px-4 py-3 min-w-[180px] max-w-[220px] border-l-[4px] cursor-pointer transition-all duration-150',
      border,
      s.inferred && 'border-dashed',
      data.selected && 'ring-2 ring-primary-400 shadow-glow',
    )}>
      <Handle type="target" position={Position.Left} className="!bg-primary-400 !w-2 !h-2 !border-white !border-2" />
      <div className="flex items-center gap-2 mb-1.5">
        <span className={clsx('text-[8px] tracking-[1.5px] font-bold uppercase px-1.5 py-0.5 rounded', badge)}>
          {s.kind === 'normal' ? 'STEP' : s.kind.toUpperCase()}
        </span>
        {s.inferred && <span className="text-[8px] text-amber-500 font-medium">INFERRED</span>}
      </div>
      <p className="text-[11px] font-semibold text-ink leading-snug line-clamp-3">{s.name}</p>
      {s.actor && <p className="text-[9px] text-muted mt-1">👤 {s.actor}</p>}
      <Handle type="source" position={Position.Right} className="!bg-primary-400 !w-2 !h-2 !border-white !border-2" />
    </div>
  );
}

// ── Custom Edge ──
function WorkflowEdge(props: any) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, style, markerEnd } = props;
  const [path, labelX, labelY] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, borderRadius: 16 });
  return (
    <>
      <BaseEdge path={path} style={style} markerEnd={markerEnd} />
      {data?.label && (
        <foreignObject x={labelX - 60} y={labelY - 14} width={120} height={28} className="pointer-events-none">
          <div className="bg-white/90 backdrop-blur-sm border border-surface-300 rounded-md px-2 py-0.5 text-[9px] text-muted font-medium text-center truncate shadow-sm">
            {data.label}
          </div>
        </foreignObject>
      )}
    </>
  );
}

const nodeTypes: NodeTypes = { workflow: WorkflowNode as any };
const edgeTypes: EdgeTypes = { workflow: WorkflowEdge as any };

// ── Dagre layout ──
function layout(states: State[], transitions: Transition[]) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'LR', ranksep: 120, nodesep: 60, marginx: 40, marginy: 40 });
  g.setDefaultEdgeLabel(() => ({}));
  states.forEach(s => g.setNode(s.id, { width: 200, height: 80 }));
  transitions.forEach(t => g.setEdge(t.source, t.target));
  dagre.layout(g);

  const nodes: Node[] = states.map(s => {
    const pos = g.node(s.id);
    return { id: s.id, type: 'workflow', position: { x: pos.x - 100, y: pos.y - 40 }, data: { state: s } };
  });

  const edges: Edge[] = transitions.map(t => ({
    id: t.id,
    source: t.source,
    target: t.target,
    type: 'workflow',
    data: { label: t.condition || t.label || '', transition: t },
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: '#a0b5a1' },
    style: { stroke: '#a0b5a1', strokeWidth: 2 },
    animated: true,
  }));

  return { nodes, edges };
}

// ── Main Component ──
interface Props {
  process: Process;
  onNodeClick?: (state: State) => void;
  onEdgeClick?: (transition: Transition) => void;
  className?: string;
}

export default function WorkflowGraph({ process, onNodeClick, onEdgeClick, className }: Props) {
  const { nodes: init, edges: initEdges } = useMemo(
    () => layout(process.states, process.transitions),
    [process],
  );
  const [nodes, setNodes, onNodesChange] = useNodesState(init);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initEdges);

  useEffect(() => {
    const { nodes: n, edges: e } = layout(process.states, process.transitions);
    setNodes(n);
    setEdges(e);
  }, [process, setNodes, setEdges]);

  const handleNodeClick = useCallback((_: unknown, node: Node) => {
    const state = process.states.find(s => s.id === node.id);
    if (state && onNodeClick) onNodeClick(state);
  }, [process, onNodeClick]);

  const handleEdgeClick = useCallback((_: unknown, edge: Edge) => {
    const transition = process.transitions.find(t => t.id === edge.id);
    if (transition && onEdgeClick) onEdgeClick(transition);
  }, [process, onEdgeClick]);

  if (!process.states.length) {
    return (
      <div className={clsx('flex items-center justify-center h-64 rc-card', className)}>
        <p className="text-sm text-muted italic">No workflow steps extracted</p>
      </div>
    );
  }

  return (
    <div className={clsx('rc-card overflow-hidden', className)} style={{ height: 480 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        className="bg-surface-50"
      >
        <Background color="#c6d3c4" gap={22} size={1} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={node => {
            const s = (node.data as any)?.state;
            if (s?.kind === 'start') return '#bbf7d0';
            if (s?.kind === 'terminal') return '#99f6e4';
            return '#e5e7eb';
          }}
          maskColor="rgba(246,247,243,0.7)"
        />
      </ReactFlow>
    </div>
  );
}
