'use client';

import React from 'react';
import { Issue } from '@/types';
import { IssueCard } from '@/components/IssueCard';

interface BoardColumnProps {
  column: {
    column_id: number;
    name: string;
    status_name?: string;
    status_color?: string;
    issues: Issue[];
  };
  onIssueClick: (issue: Issue) => void;
  onDrop: (issueId: number, columnId: number) => void;
}

export const BoardColumn: React.FC<BoardColumnProps> = ({ column, onIssueClick, onDrop }) => {
  const [isDragOver, setIsDragOver] = React.useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const issueId = parseInt(e.dataTransfer.getData('text/plain'), 10);
    if (issueId) {
      onDrop(issueId, column.column_id);
    }
  };

  return (
    <div
      className={`soft-panel flex-1 min-w-80 rounded-[1.6rem] p-3.5 ${
        isDragOver ? 'drop-target' : ''
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-slate-400">
            Workflow lane
          </p>
          <h3 className="mt-1 font-semibold text-slate-900">{column.name}</h3>
        </div>
        <span className="rounded-full bg-white px-2.5 py-1 text-[0.72rem] font-semibold text-slate-600 shadow-sm">
          {column.issues.length}
        </span>
      </div>

      {column.status_color && (
        <div
          className="mb-4 h-1.5 rounded-full"
          style={{ backgroundColor: column.status_color }}
        />
      )}

      <div className="space-y-2.5">
        {column.issues.map((issue) => (
          <div key={issue.issue_id} draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', issue.issue_id.toString())}>
            <IssueCard issue={issue} onClick={() => onIssueClick(issue)} />
          </div>
        ))}
      </div>
    </div>
  );
};
