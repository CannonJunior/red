"""
opportunities_tasks_mixin.py — Task management mixin for OpportunitiesManager.

Provides create_task, list_tasks, update_task, get_task, get_task_history,
delete_task, and get_pipeline_stats. Mixed into OpportunitiesManager via
inheritance; depends on self._connect() being available from the base class.
"""

import uuid
from datetime import datetime
from typing import Dict


class _TasksMixin:
    """Task management and pipeline stats methods for OpportunitiesManager."""

    # -------------------------------------------------------------------------
    # Pipeline Stats
    # -------------------------------------------------------------------------

    def get_pipeline_stats(self) -> Dict:
        """
        Compute pipeline health statistics.

        Calculates win rate, stage distribution, priority breakdown,
        and total/active/won pipeline value from current DB state.

        Returns:
            Dict with status, stats sub-dict containing all metrics.
        """
        _WON_STAGES  = {'awarded', 'contract_vehicle_won', 'contract_vehicle_complete'}
        _LOST_STAGES = {'lost', 'no_bid', 'cancelled'}
        _OPEN_STAGES = {
            'identified', 'qualifying', 'long_lead', 'bid_decision',
            'active', 'submitted', 'negotiating',
        }

        try:
            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute(
                "SELECT pipeline_stage, priority, value FROM opportunities"
            )
            rows = cursor.fetchall()

            total = len(rows)
            by_stage: Dict[str, Dict] = {}
            by_priority: Dict[str, int] = {}
            total_value = 0.0
            active_value = 0.0
            won_value = 0.0
            won_count = 0
            lost_count = 0

            for row in rows:
                stage    = row['pipeline_stage'] or 'identified'
                priority = row['priority'] or 'medium'
                value    = float(row['value'] or 0)

                if stage not in by_stage:
                    by_stage[stage] = {'count': 0, 'value': 0.0}
                by_stage[stage]['count'] += 1
                by_stage[stage]['value'] += value

                by_priority[priority] = by_priority.get(priority, 0) + 1

                total_value += value
                if stage in _WON_STAGES:
                    won_value += value
                    won_count += 1
                elif stage in _OPEN_STAGES:
                    active_value += value

                if stage in _LOST_STAGES:
                    lost_count += 1

            decided = won_count + lost_count
            win_rate = round(won_count / decided, 4) if decided > 0 else None

            return {
                'status': 'success',
                'stats': {
                    'total':         total,
                    'won_count':     won_count,
                    'lost_count':    lost_count,
                    'active_count':  sum(
                        v['count'] for s, v in by_stage.items()
                        if s in _OPEN_STAGES
                    ),
                    'win_rate':      win_rate,
                    'total_value':   round(total_value, 2),
                    'active_value':  round(active_value, 2),
                    'won_value':     round(won_value, 2),
                    'by_stage':      by_stage,
                    'by_priority':   by_priority,
                },
            }

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to compute pipeline stats: {e}'}

    # -------------------------------------------------------------------------
    # Task CRUD
    # -------------------------------------------------------------------------

    def create_task(self, opportunity_id: str, name: str, start_date: str, end_date: str,
                    description: str = "", status: str = "pending", progress: int = 0,
                    assigned_to: str = "") -> Dict:
        """
        Create a new task for an opportunity.

        Args:
            opportunity_id: Parent opportunity ID.
            name: Task name.
            start_date: Task start date (ISO format).
            end_date: Task end date (ISO format).
            description: Task description.
            status: Task status (pending, in_progress, completed).
            progress: Progress percentage (0-100).
            assigned_to: Person assigned to the task.

        Returns:
            Created task data dict.
        """
        try:
            task_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO tasks
                (id, opportunity_id, name, description, start_date, end_date,
                 status, progress, assigned_to, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, opportunity_id, name, description, start_date, end_date,
                  status, progress, assigned_to, now, now))

            conn.commit()

            return {
                'status': 'success',
                'task': {
                    'id': task_id,
                    'opportunity_id': opportunity_id,
                    'name': name,
                    'description': description,
                    'start_date': start_date,
                    'end_date': end_date,
                    'status': status,
                    'progress': progress,
                    'assigned_to': assigned_to,
                    'created_at': now,
                    'updated_at': now,
                }
            }

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to create task: {str(e)}'}

    def list_tasks(self, opportunity_id: str) -> Dict:
        """
        List all tasks for an opportunity.

        Args:
            opportunity_id: Opportunity ID.

        Returns:
            Dict with tasks list and count.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute("""
                SELECT id, opportunity_id, name, description, start_date, end_date,
                       status, progress, assigned_to, created_at, updated_at
                FROM tasks
                WHERE opportunity_id = ?
                ORDER BY start_date ASC
            """, (opportunity_id,))

            rows = cursor.fetchall()

            tasks = [{
                'id': r['id'], 'opportunity_id': r['opportunity_id'],
                'name': r['name'], 'description': r['description'],
                'start_date': r['start_date'], 'end_date': r['end_date'],
                'status': r['status'], 'progress': r['progress'],
                'assigned_to': r['assigned_to'],
                'created_at': r['created_at'], 'updated_at': r['updated_at'],
            } for r in rows]

            return {'status': 'success', 'tasks': tasks, 'count': len(tasks)}

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to list tasks: {str(e)}',
                    'tasks': [], 'count': 0}

    def update_task(self, task_id: str, edited_by: str = "system", **updates) -> Dict:
        """
        Update a task and save an edit-history snapshot.

        Args:
            task_id: Task ID.
            edited_by: User who made the edit.
            **updates: Fields to update.

        Returns:
            Updated task data dict.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute("""
                SELECT id, opportunity_id, name, description, start_date, end_date,
                       status, progress, assigned_to, created_at, updated_at
                FROM tasks WHERE id = ?
            """, (task_id,))
            current = cursor.fetchone()

            if not current:
                return {'status': 'error', 'message': 'Task not found'}

            history_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            _fields = ['name', 'description', 'start_date', 'end_date',
                       'status', 'progress', 'assigned_to']
            changes = [
                f"{f}: '{current[f] or 'None'}' → '{updates[f] or 'None'}'"
                for f in _fields
                if f in updates and updates[f] != current[f]
            ]
            change_description = "; ".join(changes) if changes else "No changes"

            cursor.execute("""
                INSERT INTO task_history
                (id, task_id, opportunity_id, name, description, start_date, end_date,
                 status, progress, assigned_to, edited_by, edited_at, change_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                history_id, task_id, current['opportunity_id'],
                current['name'], current['description'],
                current['start_date'], current['end_date'],
                current['status'], current['progress'],
                current['assigned_to'], edited_by, now, change_description,
            ))

            update_fields = [f"{f} = ?" for f in _fields if f in updates]
            update_values = [updates[f] for f in _fields if f in updates]

            if not update_fields:
                return {'status': 'error', 'message': 'No fields to update'}

            update_fields.append("updated_at = ?")
            update_values.extend([now, task_id])

            cursor.execute(
                f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?",
                update_values,
            )
            conn.commit()

            return self.get_task(task_id)

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to update task: {str(e)}'}

    def get_task(self, task_id: str) -> Dict:
        """
        Get a specific task by ID.

        Args:
            task_id: Task ID.

        Returns:
            Task data dict.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute("""
                SELECT id, opportunity_id, name, description, start_date, end_date,
                       status, progress, assigned_to, created_at, updated_at
                FROM tasks WHERE id = ?
            """, (task_id,))
            row = cursor.fetchone()

            if not row:
                return {'status': 'error', 'message': 'Task not found'}

            return {
                'status': 'success',
                'task': {
                    'id': row['id'], 'opportunity_id': row['opportunity_id'],
                    'name': row['name'], 'description': row['description'],
                    'start_date': row['start_date'], 'end_date': row['end_date'],
                    'status': row['status'], 'progress': row['progress'],
                    'assigned_to': row['assigned_to'],
                    'created_at': row['created_at'], 'updated_at': row['updated_at'],
                }
            }

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to get task: {str(e)}'}

    def get_task_history(self, task_id: str) -> Dict:
        """
        Get edit history for a task.

        Args:
            task_id: Task ID.

        Returns:
            Dict with history list and count.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute("""
                SELECT id, task_id, opportunity_id, name, description, start_date, end_date,
                       status, progress, assigned_to, edited_by, edited_at, change_description
                FROM task_history
                WHERE task_id = ?
                ORDER BY edited_at DESC
            """, (task_id,))

            rows = cursor.fetchall()

            history = [{
                'id': r['id'], 'task_id': r['task_id'],
                'name': r['name'], 'description': r['description'],
                'start_date': r['start_date'], 'end_date': r['end_date'],
                'status': r['status'], 'progress': r['progress'],
                'assigned_to': r['assigned_to'],
                'edited_by': r['edited_by'], 'edited_at': r['edited_at'],
                'change_description': r['change_description'],
            } for r in rows]

            return {'status': 'success', 'history': history, 'count': len(history)}

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to get task history: {str(e)}'}

    def delete_task(self, task_id: str) -> Dict:
        """
        Delete a task.

        Args:
            task_id: Task ID.

        Returns:
            Success status dict.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()

            return {'status': 'success', 'message': 'Task deleted successfully'}

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to delete task: {str(e)}'}
