
import pandas as pd

# Load the Excel file
input_file = "input_data.xlsx"
output_file = "output_file.xlsx"

# Reading worksheets
ip_1 = pd.read_excel(input_file, sheet_name="ip_1")
ip_2 = pd.read_excel(input_file, sheet_name="ip_2")
ip_3 = pd.read_excel(input_file, sheet_name="ip_3")
ip_4 = pd.read_excel(input_file, sheet_name="ip_4")

# Settings
buffer = 0  # Buffer for students per room
dense_mode = True  # If True, allocate fully; If False, allocate up to 50% per course
max_fill = 1.0 if dense_mode else 0.5

# Step 1: Prepare Data
course_roll_mapping = ip_1.groupby("course_code")["rollno"].apply(list).to_dict()
exam_schedule = ip_2.set_index("Date").to_dict(orient="index")
rooms = ip_3.sort_values(by=["Block", "Exam Capacity"], ascending=[True, False])
room_capacity = rooms.set_index("Room No.")["Exam Capacity"].to_dict()
room_block = rooms.set_index("Room No.")["Block"].to_dict()

# Count the number of students in each course
course_student_count = ip_1.groupby("course_code")["rollno"].nunique()

# Step 2: Allocate Seating
seating_plan = []

# Store the initial capacity of each room before any allocation happens
initial_room_capacity = room_capacity.copy()

# Allocate seating for all courses on all dates and sessions
for date, schedule in exam_schedule.items():
    for session in ["Morning", "Evening"]:
        if pd.isna(schedule[session]) or schedule[session] == "NO EXAM":
            continue
        
        # Reset vacant rooms at the beginning of each session
        vacant_rooms_block9 = {room: capacity - buffer for room, capacity in room_capacity.items() if room_block[room] == 9}
        vacant_rooms_lt = {room: capacity - buffer for room, capacity in room_capacity.items() if room_block[room] != 9}

        # Extract courses for the session
        courses = schedule[session].split("; ")
        courses.sort(key=lambda c: len(course_roll_mapping.get(c, [])), reverse=True)  # Large courses first
        
        # Assign rooms for each course
        for course in courses:
            rolls = course_roll_mapping.get(course, [])
            total_students = len(rolls)
            if total_students == 0:
                continue
            
            # First, attempt allocation in Block 9
            allocated_students = 0
            allocated_rolls = []
            for room, capacity in list(vacant_rooms_block9.items()):
                effective_capacity = max(capacity, 0)  # Ensure non-negative capacity
                if effective_capacity <= 0:
                    continue
                
                # If dense_mode is False, allocate at most 50% of the initial room capacity
                max_alloc = int(initial_room_capacity[room] * max_fill)
                alloc = min(total_students, max_alloc)

                # Allocate students
                allocated_rolls.extend(rolls[:alloc])
                rolls = rolls[alloc:]
                total_students -= alloc
                
                # Record seating allocation
                seating_plan.append([date, schedule["Day"], session, course, room, alloc, ";".join(allocated_rolls)])
                vacant_rooms_block9[room] -= alloc
                
                # Remove room if filled
                if vacant_rooms_block9[room] <= 0:
                    del vacant_rooms_block9[room]
                
                if total_students == 0:
                    break
            
            # If Block 9 cannot accommodate all students, shift entirely to LT
            if total_students > 0:
                allocated_rolls = []
                for room, capacity in list(vacant_rooms_lt.items()):
                    effective_capacity = max(capacity, 0)  # Ensure non-negative capacity
                    if effective_capacity <= 0:
                        continue
                    
                    # If dense_mode is False, allocate at most 50% of the initial room capacity
                    max_alloc = int(initial_room_capacity[room] * max_fill)
                    alloc = min(total_students, max_alloc)
                    
                    # Allocate students
                    allocated_rolls.extend(rolls[:alloc])
                    rolls = rolls[alloc:]
                    total_students -= alloc
                    
                    # Record seating allocation
                    seating_plan.append([date, schedule["Day"], session, course, room, alloc, ";".join(allocated_rolls)])
                    vacant_rooms_lt[room] -= alloc
                    
                    # Remove room if filled
                    if vacant_rooms_lt[room] <= 0:
                        del vacant_rooms_lt[room]
                    
                    if total_students == 0:
                        break

            # Update remaining unallocated students
            if total_students > 0:
                course_roll_mapping[course] = rolls
            else:
                del course_roll_mapping[course]


# Step 3: Prepare Room Vacancy Status
room_vacancy_status = [
    [room, capacity, rooms.loc[rooms["Room No."] == room, "Block"].values[0], vacant_rooms_block9.get(room, vacant_rooms_lt.get(room, 0))]
    for room, capacity in room_capacity.items()
]

# Step 4: Save to Excel
op_1 = pd.DataFrame(seating_plan, columns=["Date", "Day", "Session", "course_code", "Room", "Allocated_students_count", "Roll_list"])
op_2 = pd.DataFrame(room_vacancy_status, columns=["Room No.", "Exam Capacity", "Block", "Vacant"])

with pd.ExcelWriter(output_file) as writer:
    op_1.to_excel(writer, sheet_name="op_1", index=False)
    op_2.to_excel(writer, sheet_name="op_2", index=False)

print(f"Seating plan and room vacancy status written to {output_file}")

