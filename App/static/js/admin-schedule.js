document.addEventListener('DOMContentLoaded', function() {
  // --- Drag and Drop Functionality ---
  initializeDragAndDrop();
  
  // --- Staff Search Modal ---
  initializeStaffSearchModal();
  
  // --- Generate Schedule Button ---
  initializeGenerateButton();
  
  // --- Publish Schedule Button ---
  initializePublishButton();
  
  // --- Save Changes Button ---
  initializeSaveChangesButton();
  
  // --- Flash Message Handling ---
  handleFlashMessages();
  
  // --- Load the current schedule automatically ---
  loadCurrentSchedule();
});

function handleFlashMessages() {
  // Get all flash messages
  const flashMessages = document.querySelectorAll('.flash-message');
  
  // Set a timeout to remove each message after 5 seconds
  flashMessages.forEach(message => {
    setTimeout(() => {
      message.remove();
    }, 5000);
  });
}

function loadCurrentSchedule() {
  // Show the loading indicator
  const loadingIndicator = document.getElementById('loadingIndicator');
  loadingIndicator.style.display = 'flex';
  
  // Call the API to get the current schedule
  fetch('/api/schedule/details')
    .then(response => {
      if (!response.ok) {
        return response.json().then(errorData => {
          throw new Error(errorData.message || 'Failed to load schedule.');
        });
      }
      return response.json();
    })
    .then(data => {
      loadingIndicator.style.display = 'none';
      
      if (data.status === 'success') {
        // Store the schedule ID for saving changes and publishing
        if (data.schedule_id) {
          document.body.setAttribute('data-schedule-id', data.schedule_id);
        }
        
        // Check if schedule is already published
        if (data.is_published) {
          document.getElementById('publishSchedule').disabled = true;
          document.getElementById('publishSchedule').textContent = 'Published';
        } else {
          document.getElementById('publishSchedule').disabled = false;
          document.getElementById('publishSchedule').textContent = 'Publish Schedule';
        }
        
        renderSchedule(data.schedule, data.staff_index);
        
        // Show schedule stats
        const statsDiv = document.getElementById('scheduleStats');
        statsDiv.style.display = 'block';
        
        // Add stats
        const statsList = document.getElementById('statsList');
        statsList.innerHTML = `
          <div class="stat-item">
            <div class="stat-label">Total Staff:</div>
            <div class="stat-value">${Object.keys(data.staff_index).length}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">Total Shifts:</div>
            <div class="stat-value">40</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">Schedule Type:</div>
            <div class="stat-value">Help Desk</div>
          </div>
        `;
      } else {
        // No schedule found, hide loading indicator and show empty message
        const scheduleBody = document.getElementById('scheduleBody');
        scheduleBody.innerHTML = `
          <tr>
            <td colspan="6" class="empty-schedule">
              <p>No schedule loaded. Click "Generate Schedule" to create a new schedule.</p>
            </td>
          </tr>
        `;
      }
    })
    .catch(error => {
      loadingIndicator.style.display = 'none';
      console.error('Error loading schedule:', error);
      // Show error message
      const scheduleBody = document.getElementById('scheduleBody');
      scheduleBody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-schedule">
            <p>Error loading schedule: ${error.message || 'Unknown error'}. Click "Generate Schedule" to create a new schedule.</p>
          </td>
        </tr>
      `;
    });
}

function initializeDragAndDrop() {
  // Track the currently dragged staff element
  let draggedStaff = null;
  
  // Add event listener to all draggable elements (delegation)
  document.addEventListener('dragstart', function(e) {
    if (e.target.classList.contains('staff-name')) {
      draggedStaff = e.target;
      
      // Store the staff ID for transfer
      const staffId = e.target.getAttribute('data-staff-id');
      const staffName = e.target.textContent.replace('×', '').trim();
      e.dataTransfer.setData('text/plain', JSON.stringify({
        id: staffId,
        name: staffName
      }));
      
      // Set opacity to indicate dragging
      e.target.classList.add('dragging');
    }
  });
  
  document.addEventListener('dragend', function(e) {
    if (draggedStaff) {
      // Reset opacity
      draggedStaff.classList.remove('dragging');
      draggedStaff = null;
    }
    
    // Remove the droppable indicator from all cells
    document.querySelectorAll('.schedule-cell').forEach(cell => {
      cell.classList.remove('droppable');
      cell.classList.remove('drag-over');
    });
  });
  
  // Prevent default to allow drop
  document.addEventListener('dragover', function(e) {
    const cell = e.target.closest('.schedule-cell');
    if (cell) {
      e.preventDefault();
      
      // Get staff count to check if cell is full
      const staffCount = cell.querySelectorAll('.staff-name').length;
      
      // Add highlight only if not full
      if (staffCount < 3) {
        cell.classList.add('droppable');
      }
    }
  });
  
  // Remove highlight when leaving
  document.addEventListener('dragleave', function(e) {
    const cell = e.target.closest('.schedule-cell');
    if (cell) {
      cell.classList.remove('droppable');
      cell.classList.remove('drag-over');
    }
  });
  
  // Handle drop
  document.addEventListener('drop', function(e) {
    e.preventDefault();
    
    // Find the drop target (schedule cell)
    const cell = e.target.closest('.schedule-cell');
    
    if (cell) {
      // Remove highlight
      cell.classList.remove('droppable');
      cell.classList.remove('drag-over');
      
      // Check if cell is already full (3 staff)
      let staffContainer = cell.querySelector('.staff-container');
      if (staffContainer && staffContainer.querySelectorAll('.staff-name').length >= 3) {
        return; // Cell is full
      }
      
      // Get the staff data
      try {
        const staffData = JSON.parse(e.dataTransfer.getData('text/plain'));
        
        // If the dragged element exists, remove it from its original container
        if (draggedStaff) {
          draggedStaff.remove();
          
          // Check if the original container is now empty
          const originalContainer = document.querySelectorAll('.staff-container');
          originalContainer.forEach(container => {
            updateStaffCounter(container.closest('.schedule-cell'));
          });
        }
        
        // Create or get staff container
        if (!staffContainer) {
          staffContainer = document.createElement('div');
          staffContainer.className = 'staff-container';
          
          // Create staff indicator
          const indicator = document.createElement('div');
          indicator.className = 'staff-slot-indicator';
          indicator.textContent = 'Staff: 0/3';
          staffContainer.appendChild(indicator);
          
          cell.appendChild(staffContainer);
        }
        
        // Add the staff name to the container
        addStaffToContainer(staffContainer, staffData.id, staffData.name);
        
        // Update counter
        updateStaffCounter(cell);
        
        // Mark the schedule as having unsaved changes
        document.body.setAttribute('data-has-changes', 'true');
        
        // Show the save changes button
        const saveChangesBtn = document.getElementById('saveChanges');
        if (saveChangesBtn) {
          saveChangesBtn.style.display = 'inline-block';
        }
      } catch (error) {
        console.error('Error parsing staff data:', error);
      }
    }
  });
}

function addStaffToContainer(container, staffId, staffName) {
  // Create new staff element
  const staffNameElem = document.createElement('div');
  staffNameElem.className = 'staff-name';
  staffNameElem.setAttribute('draggable', 'true');
  staffNameElem.setAttribute('data-staff-id', staffId);
  staffNameElem.textContent = staffName;
  
  // Add remove button
  const removeButton = document.createElement('button');
  removeButton.className = 'remove-staff';
  removeButton.innerHTML = '&times;';
  removeButton.onclick = function(e) {
    e.stopPropagation();
    staffNameElem.remove();
    updateStaffCounter(container.closest('.schedule-cell'));
    
    // Mark the schedule as having unsaved changes
    document.body.setAttribute('data-has-changes', 'true');
    
    // Show the save changes button
    const saveChangesBtn = document.getElementById('saveChanges');
    if (saveChangesBtn) {
      saveChangesBtn.style.display = 'inline-block';
    }
  };
  staffNameElem.appendChild(removeButton);
  
  // Add to container
  container.appendChild(staffNameElem);
}

function updateStaffCounter(cell) {
  if (!cell) return;
  
  const staffContainer = cell.querySelector('.staff-container');
  if (!staffContainer) return;
  
  const staffCount = staffContainer.querySelectorAll('.staff-name').length;
  let indicator = staffContainer.querySelector('.staff-slot-indicator');
  
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.className = 'staff-slot-indicator';
    staffContainer.prepend(indicator);
  }
  
  // Update the counter text
  indicator.textContent = `Staff: ${staffCount}/3`;
  
  // Add the "add staff" button if it doesn't exist
  if (!staffContainer.querySelector('.add-staff-btn')) {
    const addButton = document.createElement('button');
    addButton.className = 'add-staff-btn';
    addButton.textContent = '+ Add Staff';
    addButton.onclick = function(e) {
      e.stopPropagation();
      openStaffSearchModal(cell);
    };
    staffContainer.appendChild(addButton);
  }
  
  // Remove the add button if maximum staff reached
  if (staffCount >= 3) {
    const addButton = staffContainer.querySelector('.add-staff-btn');
    if (addButton) {
      addButton.remove();
    }
  }
}

function initializeStaffSearchModal() {
  const modal = document.getElementById('staffSearchModal');
  const closeBtn = modal.querySelector('.close-modal');
  
  // Close when clicking the X
  closeBtn.addEventListener('click', function() {
    modal.style.display = 'none';
  });
  
  // Close when clicking outside the modal
  window.addEventListener('click', function(event) {
    if (event.target === modal) {
      modal.style.display = 'none';
    }
  });
  
  // Initialize search functionality
  const searchInput = document.getElementById('staffSearchInput');
  searchInput.addEventListener('input', function() {
    const searchTerm = this.value.toLowerCase();
    searchStaff(searchTerm);
  });
}

function openStaffSearchModal(cell) {
  const modal = document.getElementById('staffSearchModal');
  const searchInput = document.getElementById('staffSearchInput');
  
  // Clear previous search
  searchInput.value = '';
  document.getElementById('staffSearchResults').innerHTML = '';
  
  // Store the target cell as a data attribute on the modal
  modal.setAttribute('data-target-cell', cell.id);
  
  // Show the modal
  modal.style.display = 'block';
  
  // Focus the search input
  searchInput.focus();
  
  // Populate with all staff initially
  searchStaff('');
}

function searchStaff(searchTerm) {
  // Show loading indicator
  const resultsContainer = document.getElementById('staffSearchResults');
  resultsContainer.innerHTML = '<div class="loading">Loading staff...</div>';
  
  // Fetch the staff data from the API
  fetch('/api/staff')
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to fetch staff data');
      }
      return response.json();
    })
    .then(data => {
      if (!data.success) {
        throw new Error(data.message || 'Failed to load staff data');
      }
      
      // Filter staff based on search term
      const filteredStaff = data.staff.filter(staff => 
        staff.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        staff.id.toLowerCase().includes(searchTerm.toLowerCase())
      );
      
      // Display results
      resultsContainer.innerHTML = '';
      
      if (filteredStaff.length === 0) {
        resultsContainer.innerHTML = '<div class="search-result-item">No staff found</div>';
        return;
      }
      
      filteredStaff.forEach(staff => {
        const resultItem = document.createElement('div');
        resultItem.className = 'search-result-item';
        resultItem.textContent = staff.name;
        resultItem.setAttribute('data-staff-id', staff.id);
        
        resultItem.addEventListener('click', function() {
          selectStaffMember(staff.id, staff.name);
        });
        
        resultsContainer.appendChild(resultItem);
      });
    })
    .catch(error => {
      console.error('Error loading staff data:', error);
      resultsContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    });
}

function selectStaffMember(staffId, staffName) {
  const modal = document.getElementById('staffSearchModal');
  const targetCellId = modal.getAttribute('data-target-cell');
  const targetCell = document.getElementById(targetCellId) || 
                     document.querySelector(`.schedule-cell[data-id="${targetCellId}"]`);
  
  if (targetCell) {
    let staffContainer = targetCell.querySelector('.staff-container');
    
    // Check if the cell already has this staff member
    const existingStaff = staffContainer.querySelectorAll('.staff-name');
    for (let i = 0; i < existingStaff.length; i++) {
      if (existingStaff[i].getAttribute('data-staff-id') == staffId) {
        // Staff already exists in this cell
        modal.style.display = 'none';
        return;
      }
    }
    
    // Check if the container is full
    if (existingStaff.length >= 3) {
      alert('This shift already has the maximum number of staff (3)');
      modal.style.display = 'none';
      return;
    }
    
    // Add the staff to the container
    addStaffToContainer(staffContainer, staffId, staffName);
    
    // Update counter
    updateStaffCounter(targetCell);
    
    // Mark the schedule as having unsaved changes
    document.body.setAttribute('data-has-changes', 'true');
    
    // Show the save changes button
    const saveChangesBtn = document.getElementById('saveChanges');
    if (saveChangesBtn) {
      saveChangesBtn.style.display = 'inline-block';
    }
  }
  
  // Close the modal
  modal.style.display = 'none';
}

function initializeGenerateButton() {
  const generateBtn = document.getElementById('generateSchedule');
  const loadingIndicator = document.getElementById('loadingIndicator');
  
  // Add a "Save Changes" button next to the Generate button if it doesn't exist
  const saveChangesBtn = document.createElement('button');
  saveChangesBtn.className = 'btn btn-primary';
  saveChangesBtn.id = 'saveChanges';
  saveChangesBtn.textContent = 'Save Changes';
  saveChangesBtn.style.display = 'none'; // Hide initially
  
  // Insert the save button after the generate button
  generateBtn.parentNode.insertBefore(saveChangesBtn, generateBtn.nextSibling);
  
  generateBtn.addEventListener('click', function() {
    // Check if there are unsaved changes
    if (document.body.getAttribute('data-has-changes') === 'true') {
      if (!confirm('You have unsaved changes. Generating a new schedule will discard these changes. Continue?')) {
        return;
      }
    }
    
    loadingIndicator.style.display = 'flex';
    
    // Get the current week
    const currentDate = new Date();
    const week = currentDate.getWeek();
    
    // Call the API to generate a new schedule
    fetch('/api/schedule/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        week_number: week
      })
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(errorData => {
          throw new Error(errorData.message || 'Failed to generate schedule.');
        });
      }
      return response.json();
    })
    .then(data => {
      if (data.status === 'success') {
        // Schedule generated successfully, now load it
        loadCurrentSchedule();
        // Reset the changes flag
        document.body.removeAttribute('data-has-changes');
        // Hide the save button
        saveChangesBtn.style.display = 'none';
      } else {
        loadingIndicator.style.display = 'none';
        alert(`Failed to generate schedule: ${data.message}`);
      }
    })
    .catch(error => {
      loadingIndicator.style.display = 'none';
      console.error('Error generating schedule:', error);
      alert(`An error occurred: ${error.message || 'Unknown error'}`);
    });
  });
}

function initializePublishButton() {
  const publishBtn = document.getElementById('publishSchedule');
  
  publishBtn.addEventListener('click', function() {
    // Check if we have a schedule ID
    const scheduleId = document.body.getAttribute('data-schedule-id');
    
    if (!scheduleId) {
      alert('No schedule has been generated yet. Please generate a schedule first.');
      return;
    }
    
    // Check if there are unsaved changes
    if (document.body.getAttribute('data-has-changes') === 'true') {
      if (!confirm('You have unsaved changes. Please save your changes before publishing. Do you want to save now?')) {
        return;
      } else {
        // Save changes first
        saveScheduleChanges(() => {
          // After saving, publish the schedule
          publishSchedule(scheduleId);
        });
        return;
      }
    }
    
    // Confirm before publishing
    if (!confirm('Are you sure you want to publish this schedule? This will notify all assigned staff.')) {
      return;
    }
    
    publishSchedule(scheduleId);
  });
}

function publishSchedule(scheduleId) {
  // Show loading state
  const publishBtn = document.getElementById('publishSchedule');
  publishBtn.disabled = true;
  publishBtn.textContent = 'Publishing...';
  
  // Call the publish API
  fetch(`/api/schedule/${scheduleId}/publish`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.status === 'success') {
      // Update button state
      publishBtn.textContent = 'Published';
      alert('Schedule has been published and notifications sent to all assigned staff.');
    } else {
      // Reset button and show error
      publishBtn.disabled = false;
      publishBtn.textContent = 'Publish Schedule';
      alert(`Failed to publish schedule: ${data.message}`);
    }
  })
  .catch(error => {
    console.error('Error publishing schedule:', error);
    publishBtn.disabled = false;
    publishBtn.textContent = 'Publish Schedule';
    alert(`An error occurred: ${error.message || 'Unknown error'}`);
  });
}

function initializeSaveChangesButton() {
  // The button is created in initializeGenerateButton
  const saveChangesBtn = document.getElementById('saveChanges');
  if (!saveChangesBtn) return;
  
  saveChangesBtn.addEventListener('click', function() {
    saveScheduleChanges();
  });
}

function saveScheduleChanges(callback) {
  // Get the schedule ID
  const scheduleId = document.body.getAttribute('data-schedule-id');
  if (!scheduleId) {
    alert('No schedule loaded. Please generate a schedule first.');
    return;
  }
  
  // Show loading state
  const saveChangesBtn = document.getElementById('saveChanges');
  const originalText = saveChangesBtn.textContent;
  saveChangesBtn.disabled = true;
  saveChangesBtn.textContent = 'Saving...';
  
  // Collect the current schedule data
  const scheduleData = collectScheduleData();
  
  // Call the API to save the changes
  fetch(`/api/schedule/${scheduleId}/update`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(scheduleData)
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(errorData => {
        throw new Error(errorData.message || 'Failed to save schedule changes.');
      });
    }
    return response.json();
  })
  .then(data => {
    saveChangesBtn.disabled = false;
    
    if (data.status === 'success') {
      // Reset the changes flag
      document.body.removeAttribute('data-has-changes');
      // Hide the save button
      saveChangesBtn.style.display = 'none';
      
      alert('Schedule changes saved successfully.');
      
      // Call the callback if provided
      if (callback && typeof callback === 'function') {
        callback();
      }
    } else {
      saveChangesBtn.textContent = originalText;
      alert(`Failed to save changes: ${data.message}`);
    }
  })
  .catch(error => {
    console.error('Error saving schedule changes:', error);
    saveChangesBtn.disabled = false;
    saveChangesBtn.textContent = originalText;
    alert(`An error occurred: ${error.message || 'Unknown error'}`);
  });
}

function collectScheduleData() {
  // Collect all the schedule data from the UI
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
  const timeSlots = ["9:00 am", "10:00 am", "11:00 am", "12:00 pm", 
                     "1:00 pm", "2:00 pm", "3:00 pm", "4:00 pm"];
  const schedule = [];
  
  // For each day
  days.forEach((day, dayIndex) => {
    const dayShifts = [];
    
    // For each time slot
    timeSlots.forEach((timeSlot, timeIndex) => {
      const cellId = `cell-${dayIndex}-${timeIndex}`;
      const cell = document.getElementById(cellId);
      
      if (cell) {
        const staffContainer = cell.querySelector('.staff-container');
        const staffElements = staffContainer ? staffContainer.querySelectorAll('.staff-name') : [];
        const staffIds = Array.from(staffElements).map(el => el.getAttribute('data-staff-id'));
        
        dayShifts.push({
          time: timeSlot,
          staff: staffIds
        });
      } else {
        // If cell not found, add empty shift
        dayShifts.push({
          time: timeSlot,
          staff: []
        });
      }
    });
    
    schedule.push({
      day: day,
      shifts: dayShifts
    });
  });
  
  return { schedule };
}

function renderSchedule(schedule, staffIndex) {
  const scheduleBody = document.getElementById('scheduleBody');
  scheduleBody.innerHTML = '';
  
  // For the help desk, we have hourly slots from 9am to 4pm
  const timeSlots = ["9:00 am", "10:00 am", "11:00 am", "12:00 pm", 
                    "1:00 pm", "2:00 pm", "3:00 pm", "4:00 pm"];
  
  // Create a row for each time slot
  timeSlots.forEach((timeSlot, timeIndex) => {
    const row = document.createElement('tr');
    
    // Add time cell
    const timeCell = document.createElement('td');
    timeCell.className = 'time-cell';
    timeCell.textContent = timeSlot;
    row.appendChild(timeCell);
    
    // Add cells for each day
    schedule.forEach((day, dayIndex) => {
      const shift = day.shifts[timeIndex];
      const cell = document.createElement('td');
      cell.className = 'schedule-cell';
      
      // Set unique id and data attributes for the cell
      const cellId = `cell-${dayIndex}-${timeIndex}`;
      cell.id = cellId;
      cell.setAttribute('data-day', day.day);
      cell.setAttribute('data-time', timeSlot);
      cell.setAttribute('data-id', cellId);
      
      const staffContainer = document.createElement('div');
      staffContainer.className = 'staff-container';
      
      // Show the number of staff assigned
      const staffIndicator = document.createElement('div');
      staffIndicator.className = 'staff-slot-indicator';
      
      if (shift && shift.staff && shift.staff.length > 0) {
        staffIndicator.textContent = `Staff: ${shift.staff.length}/3`;
        
        // Add each staff member
        shift.staff.forEach(staffId => {
          if (staffIndex[staffId]) {
            addStaffToContainer(staffContainer, staffId, staffIndex[staffId]);
          }
        });
      } else {
        staffIndicator.textContent = 'Staff: 0/3';
      }
      
      staffContainer.appendChild(staffIndicator);
      
      // Add "Add Staff" button
      const addButton = document.createElement('button');
      addButton.className = 'add-staff-btn';
      addButton.textContent = '+ Add Staff';
      addButton.onclick = function(e) {
        e.stopPropagation();
        openStaffSearchModal(cell);
      };
      
      // Only add the button if there's room for more staff
      if (!shift || !shift.staff || shift.staff.length < 3) {
        staffContainer.appendChild(addButton);
      }
      
      cell.appendChild(staffContainer);
      row.appendChild(cell);
    });
    
    scheduleBody.appendChild(row);
  });
}

// Helper to get the week number
Date.prototype.getWeek = function() {
  // Create a copy of this date object
  var target = new Date(this.valueOf());

  // ISO week date weeks start on Monday, so correct the day number
  var dayNum = (this.getDay() + 6) % 7;

  // Set the target to the Thursday of this week
  target.setDate(target.getDate() - dayNum + 3);

  // ISO 8601 states that week 1 is the week with the first Thursday of that year
  var jan4 = new Date(target.getFullYear(), 0, 4);

  // Number of days from target date to jan 4
  var dayDiff = (target - jan4) / 86400000;

  // Calculate week number: Week 1 + number of weeks between target date and jan 4
  var weekNum = 1 + Math.ceil(dayDiff / 7);

  return weekNum;
};