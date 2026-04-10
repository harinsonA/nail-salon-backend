// 20241129220314
// https://cdn.datatables.net/plug-ins/2.1.8/i18n/es-CL.json
ICON_PREVIOUS = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-caret-left" viewBox="0 0 16 16">
  <path d="M10 12.796V3.204L4.519 8zm-.659.753-5.48-4.796a1 1 0 0 1 0-1.506l5.48-4.796A1 1 0 0 1 11 3.204v9.592a1 1 0 0 1-1.659.753"/>
</svg>`;
ICON_NEXT = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-caret-right" viewBox="0 0 16 16">
  <path d="M6 12.796V3.204L11.481 8zm.659.753 5.48-4.796a1 1 0 0 0 0-1.506L6.66 2.451C6.011 1.885 5 2.345 5 3.204v9.592a1 1 0 0 0 1.659.753"/>
</svg>`;

DATATABLES_LANGUAGE = {
  "aria": {
    "sortAscending": ": orden ascendente",
    "sortDescending": ": orden descendente"
  },
  "autoFill": {
    "cancel": "Cancelar",
    "fill": "Rellenar todas las celdas con <i>%d&lt;\\/i&gt;</i>",
    "fillHorizontal": "Rellenar celdas horizontalmente",
    "fillVertical": "Rellenar celdas verticalmente"
  },
  "buttons": {
    "collection": "Colección <span class=\"ui-button-icon-primary ui-icon ui-icon-triangle-1-s\"></span>",
    "colvis": "Visibilidad de la columna",
    "colvisRestore": "Restaurar visibilidad",
    "copy": "Copiar",
    "copyKeys": "Presiona ctrl or u2318 + C para copiar los datos de la tabla al portapapeles.<br /><br />Para cancelar, haz click en este mensaje o presiona esc.",
    "copyTitle": "Copiado al portapapeles",
    "csv": "CSV",
    "excel": "Excel",
    "pdf": "PDF",
    "print": "Imprimir",
    "copySuccess": {
      "1": "Copiaste un registro al portapapeles",
      "_": "Copiaste %ds registros al portapapeles"
    },
    "pageLength": {
      "-1": "Mostrar todos",
      "_": "Mostrar %ds filas"
    },
    "createState": "Crear Estado",
    "removeAllStates": "Eliminar Todos los Estados",
    "removeState": "Eliminar",
    "renameState": "Renombrar",
    "savedStates": "Estados Guardados",
    "stateRestore": "Estado %d",
    "updateState": "Actualizar"
  },
  "datetime": {
    "amPm": [
      "AM",
      "PM"
    ],
    "hours": "Horas",
    "minutes": "Minutos",
    "months": {
      "0": "Enero",
      "1": "Febrero",
      "2": "Marzo",
      "3": "Abril",
      "4": "Mayo",
      "5": "Junio",
      "6": "Julio",
      "7": "Agosto",
      "8": "Septiembre",
      "9": "Octubre",
      "10": "Noviembre",
      "11": "Diciembre"
    },
    "next": ICON_NEXT,
    "previous": ICON_PREVIOUS,
    "seconds": "Segundos",
    "weekdays": [
      "Dom",
      "Lun",
      "Mar",
      "Mie",
      "Jue",
      "Vie",
      "Sab"
    ],
    "unknown": "-"
  },
  "decimal": ",",
  "editor": {
    "close": "Cerrar",
    "create": {
      "button": "Nuevo",
      "submit": "Crear",
      "title": "Crear nuevo registro"
    },
    "edit": {
      "button": "Editar",
      "submit": "Actualizar",
      "title": "Editar registro"
    },
    "error": {
      "system": "Ocurrió un error de sistema (&lt;a target=\"\\\"rel=\"nofollow\"href=\"\\\"&gt;Más información)."
    },
    "multi": {
      "info": "Los elementos seleccionados contienen diferentes valores para esta entrada. Para editar y configurar todos los elementos de esta entrada con el mismo valor, haga clic o toque aquí, de lo contrario, conservarán sus valores individuales.",
      "noMulti": "Esta entrada se puede editar individualmente, pero no como parte de un grupo.",
      "restore": "Deshacer cambios",
      "title": "Múltiples valores"
    },
    "remove": {
      "button": "Eliminar",
      "submit": "Eliminar",
      "title": "Eliminar registro",
      "confirm": {
        "1": "¿Estás seguro de que deseas eliminar 1 registro?",
        "_": "¿Estás seguro de que deseas eliminar %d registros?"
      }
    }
  },
  "emptyTable": "Sin registros",
  "info": "Mostrando _START_ a _END_ de _TOTAL_ registros",
  "infoEmpty": "Mostrando 0 a 0 de 0 registros",
  "infoFiltered": "(filtrado de _MAX_ registros)",
  "infoThousands": ".",
  "lengthMenu": "Mostrar _MENU_ registros",
  "loadingRecords": "Cargando...",
  "paginate": {
    "first": "Primero",
    "last": "Último",
    "next": ICON_NEXT,
    "previous": ICON_PREVIOUS
  },
  "processing": "Procesando...",
  "search": "Buscar:",
  "searchBuilder": {
    "add": "Agregar Condición",
    "button": {
      "0": "Filtrar",
      "_": "Filtros (%d)"
    },
    "clearAll": "Limpiar Todo",
    "condition": "Condición",
    "conditions": {
      "array": {
        "contains": "Contiene",
        "empty": "Vacío",
        "equals": "Igual",
        "not": "Distinto",
        "notEmpty": "No vacío",
        "without": "Sin"
      },
      "date": {
        "after": "Mayor",
        "before": "Menor",
        "between": "Entre",
        "empty": "Vacío",
        "equals": "Igual",
        "not": "Distinto",
        "notBetween": "No entre",
        "notEmpty": "No vacío"
      },
      "number": {
        "between": "Entre",
        "empty": "Vacío",
        "equals": "Igual",
        "gt": "Mayor",
        "gte": "Mayor o igual",
        "lt": "Menor",
        "lte": "Menor o igual",
        "not": "Distinto",
        "notBetween": "No entre",
        "notEmpty": "No vacío"
      },
      "string": {
        "contains": "Contiene",
        "empty": "Vacío",
        "endsWith": "Termina con",
        "equals": "Igual",
        "not": "Distinto",
        "notEmpty": "No vacío",
        "startsWith": "Comienza con",
        "notContains": "No contiene",
        "notStartsWith": "No comienza con",
        "notEndsWith": "No termina con"
      }
    },
    "data": "Datos",
    "deleteTitle": "Eliminar regla de filtrado",
    "leftTitle": "Filtros anulados",
    "logicAnd": "Y",
    "logicOr": "O",
    "rightTitle": "Filtro",
    "title": {
      "0": "Filtrar",
      "_": "Filtros (%d)"
    },
    "value": "Valor"
  },
  "searchPanes": {
    "clearMessage": "Limpiar todo",
    "collapse": {
      "0": "Paneles de búsqueda",
      "_": "Paneles de búsqueda (%d)"
    },
    "count": "{total}",
    "countFiltered": "{shown} ({total})",
    "emptyPanes": "Sin paneles de búsqueda",
    "loadMessage": "Cargando paneles de búsqueda...",
    "title": "Filtros activos - %d",
    "showMessage": "Mostrar Todos",
    "collapseMessage": "Colapsar Todos"
  },
  "select": {
    "cells": {
      "1": "Una celda seleccionada",
      "_": "%d celdas seleccionadas"
    },
    "columns": {
      "1": "Una columna seleccionada",
      "_": "%d columnas seleccionadas"
    },
    "rows": {
      "1": "Una fila seleccionada",
      "_": "%d filas seleccionadas"
    }
  },
  "thousands": ".",
  "zeroRecords": "No se encontraron registros",
  "searchPlaceholder": "",
  "stateRestore": {
    "creationModal": {
      "button": "Crear",
      "columns": {
        "search": "Búsqueda de Columnas",
        "visible": "Visibilidad de Columnas"
      },
      "name": "Nombre:",
      "order": "Ordenamiento",
      "paging": "Paginación",
      "scroller": "Posición del Scroll",
      "search": "Búsqueda",
      "searchBuilder": "Constructor de Búsquedas",
      "select": "Seleccionar",
      "title": "Crear un Nuevo Estado",
      "toggleLabel": "Incluir:"
    },
    "duplicateError": "Ya existe un estado con este nombre.",
    "emptyError": "El nombre no puede estar vacío.",
    "emptyStates": "No hay estados guardados",
    "removeConfirm": "¿Estás seguro de que deseas eliminar %s?",
    "removeError": "Hubo un error al eliminar el estado",
    "removeJoiner": "y",
    "removeSubmit": "Eliminar",
    "removeTitle": "Eliminar Estado",
    "renameButton": "Renombrar",
    "renameLabel": "Nombre nuevo para %s:",
    "renameTitle": "Renombrar Estado"
  }
}