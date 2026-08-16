from django.urls import path
from apps.tareas.views import TaskDetailModalView, TaskListView, TaskView

urlpatterns = [
    path(
        "procesos/",
        TaskView.as_view(),
        name="tasks",
    ),
    path(
        "procesos/lista/ajax",
        TaskListView.as_view(),
        name="task_list",
    ),
    path(
        "procesos/<int:pk>/detalle/",
        TaskDetailModalView.as_view(),
        name="task_detail_modal",
    ),
]
