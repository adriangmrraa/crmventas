import { useState, useEffect, useCallback } from 'react';
import { CheckSquare, Plus, Trash2, Calendar, Loader2 } from 'lucide-react';
import api from '../../api/axios';

const CRM_TASKS_BASE = '/admin/core/crm/tasks';

interface Task {
  id: string;
  lead_id: string;
  title: string;
  priority: 'urgent' | 'high' | 'medium' | 'low';
  status: string;
  due_date: string | null;
  created_at: string;
}

interface TaskSectionProps {
  leadId: string;
}

const PRIORITY_STYLES: Record<string, { badge: string; label: string }> = {
  urgent: { badge: 'bg-red-500/10 text-red-400', label: 'Urgente' },
  high: { badge: 'bg-orange-500/10 text-orange-400', label: 'Alta' },
  medium: { badge: 'bg-blue-500/10 text-blue-400', label: 'Media' },
  low: { badge: 'bg-gray-500/10 text-gray-400', label: 'Baja' },
};

export default function TaskSection({ leadId }: TaskSectionProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Quick-add form state
  const [newTitle, setNewTitle] = useState('');
  const [newPriority, setNewPriority] = useState<string>('medium');
  const [newDueDate, setNewDueDate] = useState('');

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<Task[]>(`${CRM_TASKS_BASE}?lead_id=${leadId}`);
      setTasks(Array.isArray(res.data) ? res.data : []);
    } catch {
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, [leadId]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleAdd = async () => {
    const title = newTitle.trim();
    if (!title) return;
    try {
      setAdding(true);
      await api.post(CRM_TASKS_BASE, {
        lead_id: leadId,
        title,
        priority: newPriority,
        due_date: newDueDate || undefined,
      });
      setNewTitle('');
      setNewDueDate('');
      setNewPriority('medium');
      await fetchTasks();
    } catch {
      // silent
    } finally {
      setAdding(false);
    }
  };

  const handleToggleStatus = async (task: Task) => {
    const newStatus = task.status === 'completed' ? 'pending' : 'completed';
    try {
      await api.patch(`${CRM_TASKS_BASE}/${task.id}`, { status: newStatus });
      setTasks((prev) =>
        prev.map((t) => (t.id === task.id ? { ...t, status: newStatus } : t))
      );
    } catch {
      // silent
    }
  };

  const handleDelete = async (taskId: string) => {
    try {
      await api.delete(`${CRM_TASKS_BASE}/${taskId}`);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      setDeleteConfirm(null);
    } catch {
      // silent
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('es-AR', { day: '2-digit', month: 'short' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
        Tareas
      </h3>

      {/* Quick-add form */}
      <div className="flex flex-wrap items-end gap-2">
        <input
          type="text"
          placeholder="Nueva tarea..."
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAdd();
            }
          }}
          className="flex-1 min-w-[180px] px-3 py-2 text-sm bg-white/[0.04] border border-white/[0.08] rounded-lg text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        />
        <select
          value={newPriority}
          onChange={(e) => setNewPriority(e.target.value)}
          className="px-2 py-2 text-sm bg-white/[0.04] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        >
          <option value="urgent">Urgente</option>
          <option value="high">Alta</option>
          <option value="medium">Media</option>
          <option value="low">Baja</option>
        </select>
        <input
          type="date"
          value={newDueDate}
          onChange={(e) => setNewDueDate(e.target.value)}
          className="px-2 py-2 text-sm bg-white/[0.04] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={adding || !newTitle.trim()}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-white text-[#0a0e1a] rounded-lg hover:bg-white/90 disabled:opacity-40 transition-colors"
        >
          {adding ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          Agregar
        </button>
      </div>

      {/* Task list */}
      {loading ? (
        <div className="flex items-center justify-center py-8 text-white/30">
          <Loader2 size={20} className="animate-spin" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-white/30 gap-2">
          <CheckSquare size={28} />
          <span className="text-sm">Sin tareas</span>
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => {
            const ps = PRIORITY_STYLES[task.priority] || PRIORITY_STYLES.medium;
            const isCompleted = task.status === 'completed';

            return (
              <div
                key={task.id}
                className="flex items-center gap-3 px-3 py-2.5 bg-white/[0.03] border border-white/[0.06] rounded-lg group"
              >
                {/* Checkbox */}
                <button
                  type="button"
                  onClick={() => handleToggleStatus(task)}
                  className={`shrink-0 w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                    isCompleted
                      ? 'bg-green-500/20 border-green-500/40 text-green-400'
                      : 'border-white/20 hover:border-white/40 text-transparent hover:text-white/20'
                  }`}
                >
                  {isCompleted && (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                      <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </button>

                {/* Title */}
                <span
                  className={`flex-1 text-sm ${
                    isCompleted ? 'line-through text-white/30' : 'text-white'
                  }`}
                >
                  {task.title}
                </span>

                {/* Priority badge */}
                <span className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded-full ${ps.badge}`}>
                  {ps.label}
                </span>

                {/* Due date */}
                {task.due_date && (
                  <span className="shrink-0 flex items-center gap-1 text-xs text-white/40">
                    <Calendar size={12} />
                    {formatDate(task.due_date)}
                  </span>
                )}

                {/* Delete */}
                {deleteConfirm === task.id ? (
                  <div className="shrink-0 flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleDelete(task.id)}
                      className="px-2 py-0.5 text-xs font-medium text-red-400 bg-red-500/10 rounded hover:bg-red-500/20 transition-colors"
                    >
                      Eliminar
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteConfirm(null)}
                      className="px-2 py-0.5 text-xs text-white/40 hover:text-white/60 transition-colors"
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setDeleteConfirm(task.id)}
                    className="shrink-0 p-1 text-white/20 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
