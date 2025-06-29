from flask import Flask, render_template, request, jsonify, redirect, url_for
from constraint import Problem, AllDifferentConstraint

app = Flask(__name__)



data = {
    'teachers': [],
    'classrooms': [],
    'groups': [],
    'subjects': [],
    'time_slots': [],
    'schedule': {},
    'constraints': {
        'teacher_unavailable': [],
        'group_unavailable': [],
        'classroom_unavailable': [],
        'preferences': []
    }
}


# временные слоты
def generate_default_time_slots():
    return [
        {"id": 1, "day": "Monday", "start": "09:00", "end": "10:30"},
        {"id": 2, "day": "Monday", "start": "10:40", "end": "12:10"},
        {"id": 3, "day": "Monday", "start": "12:40", "end": "14:10"},
        {"id": 4, "day": "Monday", "start": "14:20", "end": "15:50"},
        {"id": 5, "day": "Monday", "start": "16:00", "end": "17:30"},
        {"id": 6, "day": "Tuesday", "start": "09:00", "end": "10:30"},
        {"id": 7, "day": "Tuesday", "start": "10:40", "end": "12:10"},
        {"id": 8, "day": "Tuesday", "start": "12:40", "end": "14:10"},
        {"id": 9, "day": "Tuesday", "start": "14:20", "end": "15:50"},
        {"id": 10, "day": "Tuesday", "start": "16:00", "end": "17:30"},
        {"id": 11, "day": "Wednesday", "start": "09:00", "end": "10:30"},
        {"id": 12, "day": "Wednesday", "start": "10:40", "end": "12:10"},
        {"id": 13, "day": "Wednesday", "start": "12:40", "end": "14:10"},
        {"id": 14, "day": "Wednesday", "start": "14:20", "end": "15:50"},
        {"id": 15, "day": "Wednesday", "start": "16:00", "end": "17:30"},
        {"id": 16, "day": "Thursday", "start": "09:00", "end": "10:30"},
        {"id": 17, "day": "Thursday", "start": "10:40", "end": "12:10"},
        {"id": 18, "day": "Thursday", "start": "12:40", "end": "14:10"},
        {"id": 19, "day": "Thursday", "start": "14:20", "end": "15:50"},
        {"id": 20, "day": "Thursday", "start": "16:00", "end": "17:30"},
        {"id": 21, "day": "Friday", "start": "09:00", "end": "10:30"},
        {"id": 22, "day": "Friday", "start": "10:40", "end": "12:10"},
        {"id": 23, "day": "Friday", "start": "12:40", "end": "14:10"},
        {"id": 24, "day": "Friday", "start": "14:20", "end": "15:50"},
        {"id": 25, "day": "Friday", "start": "16:00", "end": "17:30"}
    ]


data['time_slots'] = generate_default_time_slots()


# добавить
def add_entity(entity_type, entity_data):
    if not entity_data.get('id'):
        max_id = max([e['id'] for e in data[entity_type]], default=0)
        entity_data['id'] = max_id + 1
    data[entity_type].append(entity_data)
    return entity_data

# удалить
def delete_entity(entity_type, entity_id):
    data[entity_type] = [e for e in data[entity_type] if e['id'] != entity_id]

    if entity_type in ['teachers', 'classrooms', 'groups']:
        data['subjects'] = [s for s in data['subjects']
                            if (entity_type == 'teachers' and s.get('teacher_id') != entity_id) or
                            (entity_type == 'classrooms' and s.get('classroom_id') != entity_id) or
                            (entity_type == 'groups' and entity_id not in s.get('group_ids', []))]


def get_entity(entity_type, entity_id):
    return next((e for e in data[entity_type] if e['id'] == entity_id), None)


def update_entity(entity_type, entity_id, new_data):
    entity = get_entity(entity_type, entity_id)
    if entity:
        entity.update(new_data)
        return entity
    return None


# генерация расписания
def generate_schedule():
    problem = Problem()
    subjects = data['subjects']
    time_slots = data['time_slots']
    teachers = data['teachers']
    classrooms = data['classrooms']
    groups = data['groups']

    # добавляем переменные (каждому занятию соответствует временной слот)
    for subject in subjects:
        problem.addVariable(f"subject_{subject['id']}", [ts['id'] for ts in time_slots])

    # Ограничения:
    # 1. Преподаватель не может вести два занятия одновременно
    for teacher in teachers:
        teacher_subjects = [s for s in subjects if s.get('teacher_id') == teacher['id']]
        if len(teacher_subjects) > 1:
            problem.addConstraint(AllDifferentConstraint(),
                                  [f"subject_{s['id']}" for s in teacher_subjects])

    # 2. Аудитория не может быть занята дважды одновременно
    for classroom in classrooms:
        classroom_subjects = [s for s in subjects if s.get('classroom_id') == classroom['id']]
        if len(classroom_subjects) > 1:
            problem.addConstraint(AllDifferentConstraint(),
                                  [f"subject_{s['id']}" for s in classroom_subjects])

    # 3. Группа не может быть на двух занятиях одновременно
    for group in groups:
        group_subjects = [s for s in subjects if group['id'] in s.get('group_ids', [])]
        if len(group_subjects) > 1:
            problem.addConstraint(AllDifferentConstraint(),
                                  [f"subject_{s['id']}" for s in group_subjects])

    # 4. Учет ограничений по недоступности
    for constraint in data['constraints']['teacher_unavailable']:
        teacher_subjects = [s for s in subjects if s.get('teacher_id') == constraint['teacher_id']]
        for s in teacher_subjects:
            problem.addConstraint(
                lambda slot, day=constraint['day']: get_time_slot(slot)['day'] != day,
                [f"subject_{s['id']}"]
            )

    solution = problem.getSolution()

    if not solution:
        return None

    # формирование расписания
    schedule = {}
    for subject in subjects:
        slot_id = solution[f"subject_{subject['id']}"]
        time_slot = get_time_slot(slot_id)

        if time_slot['day'] not in schedule:
            schedule[time_slot['day']] = []

        schedule_entry = {
            'subject_id': subject['id'],
            'subject_name': subject['name'],
            'teacher_id': subject.get('teacher_id'),
            'teacher_name': get_teacher_name(subject.get('teacher_id')),
            'classroom_id': subject.get('classroom_id'),
            'classroom_name': get_classroom_name(subject.get('classroom_id')),
            'group_ids': subject.get('group_ids', []),
            'group_names': [get_group_name(gid) for gid in subject.get('group_ids', [])],
            'time_slot_id': slot_id,
            'start': time_slot['start'],
            'end': time_slot['end']
        }

        schedule[time_slot['day']].append(schedule_entry)

    # сортировка по времени
    for day in schedule:
        schedule[day].sort(key=lambda x: x['start'])

    data['schedule'] = schedule
    return schedule


def get_time_slot(slot_id):
    return next((ts for ts in data['time_slots'] if ts['id'] == slot_id), None)


def get_teacher_name(teacher_id):
    teacher = get_entity('teachers', teacher_id)
    return teacher['name'] if teacher else "Не указан"


def get_classroom_name(classroom_id):
    classroom = get_entity('classrooms', classroom_id)
    return classroom['name'] if classroom else "Не указана"


def get_group_name(group_id):
    group = get_entity('groups', group_id)
    return group['name'] if group else "Не указана"


# вспомогательные функции для проверки конфликтов
def check_schedule_conflicts():
    conflicts = []
    schedule = data['schedule']

    # проверка на пересечение слотов для преподавателей, аудиторий и групп
    for day in schedule:
        entries = schedule[day]

        teachers = {}
        for entry in entries:
            if entry['teacher_id']:
                if entry['teacher_id'] not in teachers:
                    teachers[entry['teacher_id']] = []
                teachers[entry['teacher_id']].append(entry)

        for teacher_id, teacher_entries in teachers.items():
            if len(teacher_entries) > 1:
                teacher_entries.sort(key=lambda x: x['start'])
                for i in range(len(teacher_entries) - 1):
                    if teacher_entries[i]['end'] > teacher_entries[i + 1]['start']:
                        conflicts.append({
                            'type': 'teacher',
                            'teacher_id': teacher_id,
                            'teacher_name': teacher_entries[i]['teacher_name'],
                            'day': day,
                            'entry1': teacher_entries[i],
                            'entry2': teacher_entries[i + 1]
                        })

        classrooms = {}
        for entry in entries:
            if entry['classroom_id']:
                if entry['classroom_id'] not in classrooms:
                    classrooms[entry['classroom_id']] = []
                classrooms[entry['classroom_id']].append(entry)

        for classroom_id, classroom_entries in classrooms.items():
            if len(classroom_entries) > 1:
                classroom_entries.sort(key=lambda x: x['start'])
                for i in range(len(classroom_entries) - 1):
                    if classroom_entries[i]['end'] > classroom_entries[i + 1]['start']:
                        conflicts.append({
                            'type': 'classroom',
                            'classroom_id': classroom_id,
                            'classroom_name': classroom_entries[i]['classroom_name'],
                            'day': day,
                            'entry1': classroom_entries[i],
                            'entry2': classroom_entries[i + 1]
                        })

        groups = {}
        for entry in entries:
            for group_id in entry['group_ids']:
                if group_id not in groups:
                    groups[group_id] = []
                groups[group_id].append(entry)

        for group_id, group_entries in groups.items():
            if len(group_entries) > 1:
                group_entries.sort(key=lambda x: x['start'])
                for i in range(len(group_entries) - 1):
                    if group_entries[i]['end'] > group_entries[i + 1]['start']:
                        conflicts.append({
                            'type': 'group',
                            'group_id': group_id,
                            'group_name': group_entries[i]['group_names'][
                                group_entries[i]['group_ids'].index(group_id)],
                            'day': day,
                            'entry1': group_entries[i],
                            'entry2': group_entries[i + 1]
                        })

    return conflicts


# Flask
@app.route('/')
def index():
    return render_template('index.html', data=data)


# API для работы с сущностями
@app.route('/api/<entity_type>', methods=['GET', 'POST'])
def handle_entities(entity_type):
    if entity_type not in ['teachers', 'classrooms', 'groups', 'subjects', 'time_slots']:
        return jsonify({'error': 'Invalid entity type'}), 400

    if request.method == 'GET':
        return jsonify(data[entity_type])
    elif request.method == 'POST':
        entity_data = request.get_json()
        new_entity = add_entity(entity_type, entity_data)
        return jsonify(new_entity), 201


@app.route('/api/<entity_type>/<int:entity_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_entity(entity_type, entity_id):
    if entity_type not in ['teachers', 'classrooms', 'groups', 'subjects', 'time_slots']:
        return jsonify({'error': 'Invalid entity type'}), 400

    if request.method == 'GET':
        entity = get_entity(entity_type, entity_id)
        if entity:
            return jsonify(entity)
        return jsonify({'error': 'Entity not found'}), 404
    elif request.method == 'PUT':
        new_data = request.get_json()
        updated_entity = update_entity(entity_type, entity_id, new_data)
        if updated_entity:
            return jsonify(updated_entity)
        return jsonify({'error': 'Entity not found'}), 404
    elif request.method == 'DELETE':
        delete_entity(entity_type, entity_id)
        return jsonify({'message': 'Entity deleted'}), 200


# API для работы с ограничениями
@app.route('/api/constraints/<constraint_type>', methods=['GET', 'POST'])
def handle_constraints(constraint_type):
    if constraint_type not in data['constraints']:
        return jsonify({'error': 'Invalid constraint type'}), 400

    if request.method == 'GET':
        return jsonify(data['constraints'][constraint_type])
    elif request.method == 'POST':
        constraint_data = request.get_json()
        data['constraints'][constraint_type].append(constraint_data)
        return jsonify(constraint_data), 201


# API для работы с расписанием
@app.route('/api/schedule/generate', methods=['POST'])
def generate_schedule_route():
    schedule = generate_schedule()
    if schedule:
        return jsonify(schedule)
    return jsonify({'error': 'Failed to generate schedule'}), 400


@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    return jsonify(data['schedule'])


@app.route('/api/schedule/check', methods=['GET'])
def check_schedule():
    conflicts = check_schedule_conflicts()
    return jsonify(conflicts)


@app.route('/api/schedule/update', methods=['POST'])
def update_schedule_entry():
    update_data = request.get_json()
    day = update_data['day']
    entry_index = update_data['entry_index']
    new_slot_id = update_data['new_slot_id']

    if day in data['schedule'] and 0 <= entry_index < len(data['schedule'][day]):
        entry = data['schedule'][day][entry_index]
        time_slot = get_time_slot(new_slot_id)

        if time_slot:
            # Обновляем временной слот
            entry['time_slot_id'] = new_slot_id
            entry['start'] = time_slot['start']
            entry['end'] = time_slot['end']

            # Проверяем на конфликты после изменения
            conflicts = check_schedule_conflicts()
            if conflicts:
                # Откатываем изменения, если есть конфликты
                original_slot = get_time_slot(entry['time_slot_id'])
                entry['time_slot_id'] = original_slot['id']
                entry['start'] = original_slot['start']
                entry['end'] = original_slot['end']
                return jsonify({
                    'success': False,
                    'error': 'Conflict detected',
                    'conflicts': conflicts
                }), 400

            return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Invalid update data'}), 400


if __name__ == '__main__':
    app.run(debug=True)
