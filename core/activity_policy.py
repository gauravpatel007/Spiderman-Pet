"""Shared activity choices used by scheduling, manual reactions and settings."""
ACTIVITIES = {
    'idle': 'Idle / look around', 'walk': 'Walk', 'run': 'Run', 'jump': 'Jump',
    'fall': 'Falling pose', 'land': 'Landing pose', 'climb_up': 'Climb up',
    'climb_down': 'Climb down', 'wall_slide': 'Wall slide', 'perch': 'Perch',
    'swing': 'Web swing', 'hang': 'Hang', 'sleep': 'Sleep', 'wake_up': 'Wake up',
    'sit': 'Sit', 'stand_up': 'Stand up', 'wave': 'Wave', 'dance': 'Dance',
    'celebrate': 'Celebrate', 'interact': 'React to interaction', 'dragged': 'Dragging pose',
    'title_perch': 'Perch at the window’s top-right corner',
    'title_hang': 'Hang upside down from the title / tab bar',
    'focus_read': 'Read a comic quietly in focus mode',
}
LEGACY_FLAGS = {'walk':'walking', 'run':'running', 'jump':'jumping', 'sleep':'sleeping',
                'sit':'sitting', 'climb_up':'climbing', 'climb_down':'climbing',
                'swing':'swinging', 'hang':'hanging'}
PHYSICAL_STATES = {'idle','fall','land','dragged','wake_up','stand_up'}


def enabled(settings, name):
    if name in ('title_perch', 'title_hang') and not bool(settings.get('animations.enable_window_perching', True)):
        return False
    legacy = LEGACY_FLAGS.get(name)
    return bool(settings.get('animations.enabled.'+name, True)) and (
        legacy is None or bool(settings.get('behavior.enable_'+legacy, True)))
