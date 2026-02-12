# Inventario de Dominio Dental (Dentalogic v7.6)

Este documento lista todos los componentes, entidades y lógicas específicas del dominio "Dental" detectadas en el repositorio. Estos elementos deben ser abstraídos o modularizados para la transformación a una plataforma agnóstica.

## 1. Modelo de Datos (PostgreSQL)

Archivo analizado: `db/init/dentalogic_schema.sql`

### Entidades Específicas (Tablas)
*   **`clinical_records`**: Tabla central del dominio clínico.
    *   `odontogram` (JSONB): Representación gráfica de los dientes. **CRÍTICO**.
    *   `diagnosis` (TEXT): Diagnóstico médico.
    *   `radiographs` (JSONB): Imágenes de rayos X.
    *   `treatments` (JSONB): Tratamientos realizados en una sesión.
    *   `treatment_plan` (JSONB): Planificación futura.
    *   `record_date` (DATE): Fecha del registro clínico.
*   **`treatment_types`**: Catálogo de prestaciones médicas.
    *   Datos por defecto (INSERTs): "endodoncia", "extracción", "ortodoncia", "limpieza".
    *   Columnas: `complexity_level`, `requires_multiple_sessions`, `session_gap_days` (lógica de turnos médicos).
    *   Categorías: `prevention`, `surgical`, `restorative`, `orthodontics`.

### Columnas de Dominio en Entidades Core
*   **`patients`**:
    *   `insurance_provider` / `insurance_id`: Obra social / Seguro médico.
    *   `medical_history` (JSONB): Anamnesis general.
    *   `dni`: Documento nacional (común, pero obligatorio en salud argentina).
*   **`professionals`**:
    *   `specialty`: Especialidad médica (ej. Ortodoncista).
    *   `registration_id`: Matrícula profesional.
*   **`appointments`**:
    *   `urgency_level` y `urgency_reason`: Derivados del Triage médico.
    *   `chair_id`: Sillón odontológico (recurso físico).
*   **`tenants`**:
    *   `clinic_name`: Nombre de la clínica.

## 2. API Endpoints (FastAPI)

Archivo analizado: `orchestrator_service/admin_routes.py`

### Rutas con Lógica Dental Explícita
*   `GET /admin/patients/phone/{phone}/context`: Retorna `treatment_plan`, `diagnosis`, `last_appointment`. Estructura fuertemente acoplada al historial clínico.
*   `POST /admin/users/{user_id}/status`: Al aprobar un profesional, asume creación en `professionals` con campos médicos.

### Lógica de Negocio en Rutas
*   **Validación de Roles**: `role IN ('ceo', 'professional', 'secretary')`. El rol "professional" está ligado a la prestación de servicios médicos.
*   **Gestión de Turnos**: Lógica de `get_treatment_duration` basada en `treatment_types`.

## 3. Lógica del Agente (LangChain & Tools)

Archivo analizado: `orchestrator_service/main.py`

### Tools Específicas
*   **`check_availability`**:
    *   Parámetro `treatment_name`: Busca en `treatment_types` para determinar duración.
    *   Mensajes de error: "Dr/a.", "Tratamiento no disponible", "Clínica cerrada".
*   **`book_appointment`**:
    *   Parámetros: `insurance_provider`, `dni` (requeridos para `status='guest'`).
    *   Validación: Chequea `treatment_types` para duración.
    *   Mensajes de éxito: "¡Turno confirmado con el/la Dr/a...!"

### System Prompt (Implícito/Templates)
*   Aunque no se analizó el archivo de prompt crudo, la lógica en `main.py` y los mensajes de retorno de las tools contienen fraseología médica: "paciente", "turno", "obra social", "consultorio".

## 4. Frontend (React)

Archivos analizados: `frontend_react/src/views`, `locales/es.json`

### Vistas (Views)
*   **`PatientDetail.tsx`**: Visualización de `clinical_records` y **Odontograma**.
*   **`TreatmentsView.tsx`**: ABM de `treatment_types` (Precios, duraciones médicas).
*   **`ProfessionalsView.tsx`**: Gestión de "Staff Médico", especialidades, matrículas.

### Terminología (Locales `es.json`)
*   `nav.treatments`: "Tratamientos"
*   `nav.patients`: "Pacientes"
*   `nav.clinics`: "Sedes (Clínicas)"
*   `login.role_professional`: "Profesional Dental"
*   `patient_detail.odontogram`: "Odontograma"
*   `patient_detail.anamnesis`: "Anamnesis"
*   `common.urgencies`: "Urgencias"

## Resumen de Impacto
La transformación a "Agnóstico" requerirá:
1.  **Renombrar/Abstraer Entidades**: `Patients` -> `Contacts/Clients`, `Professionals` -> `Agents/Staff`, `Appointments` -> `Bookings`, `Treatments` -> `Services`.
2.  **Módulos de Nicho**: Extraer `clinical_records` y `odontogram` a un módulo `dental_module` o extensiones de esquema JSONB.
3.  **Configuración de Triage**: Parametrizar la lógica de urgencia.
4.  **UI Pluggable**: El Odontograma debe ser un componente inyectado dinámicamente según el nicho.
