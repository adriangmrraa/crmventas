# FIX-05: Internal Chat Media Upload + Notification Cards

## Intent

Extender el chat interno para soportar envio de archivos/imagenes y asegurar que las tarjetas de notificacion (llamadas y tareas) se activen con datos reales del backend, no solo como stubs visuales.

## Requirements

### MUST

- M1: Agregar boton de upload de archivo junto al boton de enviar en el input area
- M2: Al subir un archivo, hacer POST a `/api/v1/drive/files/upload` y enviar un mensaje con `tipo='mensaje'` y `metadata` conteniendo `file_url`, `file_name` y `mime_type`
- M3: Renderizar mensajes con `metadata.file_url` como links de descarga con icono MIME (reutilizar `DriveFileIcon`)
- M4: Preview inline para archivos con MIME type `image/*` (thumbnail clickeable que abre la imagen completa)
- M5: Verificar que `notificar_llamada_en_chat()` del backend se invoca cuando se crean eventos de agenda; si no se invoca, agregar la llamada en el flujo de creacion de eventos

### SHOULD

- S1: Mostrar indicador de progreso durante la subida del archivo
- S2: Limitar tamanio maximo de archivo a 10MB con mensaje de error claro
- S3: Soportar drag-and-drop de archivos sobre el area de mensajes

## Current State (lo que esta roto)

### Problema 1: Sin soporte de archivos
`InternalChatView.tsx` (linea 160-169) solo envia mensajes de texto via `handleSend()`. No existe boton de upload, ni logica para subir archivos, ni renderizado de mensajes con archivos adjuntos.

El input area (lineas 311-329) contiene unicamente un `<textarea>` y un boton `<Send>`. No hay `<input type="file">` ni boton de adjuntar.

### Problema 2: Notification cards son stubs visuales
Las tarjetas de notificacion de llamada (lineas 272-282, estilo amber) y tarea (lineas 283-290, estilo violet) existen en el JSX y renderizan correctamente cuando `msg.tipo === 'notificacion_llamada'` o `'notificacion_tarea'`, pero el backend nunca publica mensajes con estos tipos en los canales, por lo que las tarjetas nunca aparecen en produccion.

### Problema 3: Constraint de base de datos
La tabla `chat_mensajes.tipo` tiene un CHECK constraint que solo permite `'mensaje'`, `'notificacion_tarea'`, `'notificacion_llamada'`. No se necesita agregar `'file'` como nuevo tipo porque la solucion usa `tipo='mensaje'` con metadata.

## Solution

### Upload de archivos (Frontend)

1. Agregar un `<input type="file" ref={fileInputRef} hidden>` y un boton `<Paperclip>` junto al boton `<Send>` en el area de input (linea 322)
2. Al seleccionar archivo:
   - Validar tamanio (max 10MB)
   - Mostrar indicador de progreso (estado `uploading`)
   - POST a `/api/v1/drive/files/upload` con `FormData`
   - Con la URL devuelta, enviar mensaje via `POST /admin/core/internal-chat/mensajes` con:
     ```json
     {
       "canal_id": "...",
       "contenido": "nombre_archivo.pdf",
       "tipo": "mensaje",
       "metadata": {
         "file_url": "https://...",
         "file_name": "nombre_archivo.pdf",
         "mime_type": "application/pdf"
       }
     }
     ```
3. En el renderizado de mensajes, detectar `msg.metadata?.file_url` y mostrar:
   - Para `image/*`: thumbnail inline (max 300px width) con click para abrir en nueva tab
   - Para otros MIME: icono via `<DriveFileIcon>` + nombre de archivo como link de descarga

### Notification cards (Backend)

1. Verificar en el servicio de agenda/eventos que al crear un evento tipo "llamada" se invoque `notificar_llamada_en_chat()` para publicar un mensaje con `tipo='notificacion_llamada'` en el canal correspondiente
2. Si la funcion existe pero no se invoca, agregar la llamada en el flujo de creacion de eventos de agenda
3. Idem para `notificacion_tarea` si existe un flujo de tareas que deberia notificar

## Files to Modify

| Archivo | Cambio |
|---------|--------|
| `frontend_react/src/modules/crm_sales/views/InternalChatView.tsx` | Agregar upload button, file input, upload logic, file message rendering, import DriveFileIcon y Paperclip |
| `frontend_react/src/modules/crm_sales/components/drive/DriveFileIcon.tsx` | Sin cambios, solo importar |
| Backend: servicio de agenda/eventos (verificar) | Agregar llamada a `notificar_llamada_en_chat()` si falta |

## Acceptance Criteria

- [ ] AC1: El boton de adjuntar archivo aparece junto al boton de enviar
- [ ] AC2: Al seleccionar un archivo se sube a drive y se envia como mensaje con metadata
- [ ] AC3: Los mensajes con `metadata.file_url` muestran icono MIME + link de descarga
- [ ] AC4: Las imagenes se muestran como preview inline con thumbnail
- [ ] AC5: Archivos mayores a 10MB muestran error sin intentar subir
- [ ] AC6: Las notificaciones de llamada (amber card) aparecen cuando se agenda una llamada
- [ ] AC7: Los mensajes de archivo se reciben correctamente via Socket.IO en otros clientes

## Testing Strategy

### Unit Tests
- Renderizado de mensaje con `metadata.file_url` y MIME `image/png` muestra `<img>`
- Renderizado de mensaje con `metadata.file_url` y MIME `application/pdf` muestra `DriveFileIcon` + link
- Validacion de tamanio de archivo rechaza archivos > 10MB
- `handleFileUpload` llama a la API de drive y luego envia mensaje con metadata correcta

### Integration Tests
- Subir archivo → verificar que aparece en el chat como file message
- Verificar que Socket.IO propaga el file message a otros participantes del canal
- Crear evento de agenda tipo llamada → verificar que aparece la notification card amber en el canal

### Manual Tests
- Drag and drop de imagen sobre el chat (si se implementa S3)
- Verificar que el thumbnail de imagen es clickeable y abre la imagen completa
- Verificar que el link de descarga funciona para PDFs y otros archivos
