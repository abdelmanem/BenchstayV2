// Data Entry Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap components
    const editHotelModal = new bootstrap.Modal(document.getElementById('editHotelDataModal'));
    const editCompetitorModal = new bootstrap.Modal(document.getElementById('editCompetitorDataModal'));
    const deleteConfirmModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));

    // Edit Hotel Data
    document.querySelectorAll('.edit-hotel-data').forEach(button => {
        button.addEventListener('click', function() {
            const dataId = this.dataset.id;
            // Fetch hotel data and populate modal
            fetch(`/api/hotel-data/${dataId}/`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    document.getElementById('editHotelDataId').value = dataId;
                    const modalBody = document.querySelector('#editHotelDataModal .modal-body');
                    modalBody.innerHTML = `
                        <div class="form-group mb-3">
                            <label for="edit_date">Date</label>
                            <input type="date" class="form-control" id="edit_date" name="date" value="${data.date}" required>
                        </div>
                        <div class="form-group mb-3">
                            <label for="edit_rooms_sold">Rooms Sold</label>
                            <input type="number" class="form-control" id="edit_rooms_sold" name="rooms_sold" value="${data.rooms_sold}" min="0" required>
                        </div>
                        <div class="form-group mb-3">
                            <label for="edit_total_revenue">Total Revenue</label>
                            <div class="input-group">
                                <span class="input-group-text">EGP</span>
                                <input type="number" class="form-control" id="edit_total_revenue" name="total_revenue" value="${data.total_revenue}" min="0" step="0.01" required>
                            </div>
                        </div>
                        <div class="form-group mb-3">
                            <label for="edit_notes">Notes</label>
                            <textarea class="form-control" id="edit_notes" name="notes" rows="3">${data.notes || ''}</textarea>
                        </div>
                    `;
                    editHotelModal.show();
                })
                .catch(error => {
                    console.error('Error fetching hotel data:', error);
                    alert('Error loading hotel data. Please try again.');
                });
        });
    });

    // Handle Edit Hotel Data Form Submission
    document.getElementById('editHotelDataForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const dataId = document.getElementById('editHotelDataId').value;

        try {
            const response = await fetch(`/api/hotel-data/${dataId}/update/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                },
                body: formData
            });

            if (!response.ok) {
                throw new Error('Failed to update hotel data');
            }

            const result = await response.json();
            if (result.success) {
                window.location.reload();
            } else {
                alert(result.error || 'Failed to update hotel data');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error updating hotel data. Please try again.');
        }
    });

    // Edit Competitor Data
    document.querySelectorAll('.edit-competitor-data').forEach(button => {
        button.addEventListener('click', function() {
            const dataId = this.dataset.id;
            // Fetch competitor data and populate modal
            fetch(`/api/competitor-data/${dataId}/`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    document.getElementById('editCompetitorDataId').value = dataId;
                    const modalBody = document.querySelector('#editCompetitorDataModal .modal-body');
                    modalBody.innerHTML = `
                        <div class="form-group mb-3">
                            <label for="edit_competitor_date">Date</label>
                            <input type="date" class="form-control" id="edit_competitor_date" name="date" value="${data.date}" required>
                        </div>
                        <div class="form-group mb-3">
                            <label for="edit_estimated_occupancy">Estimated Occupancy (%)</label>
                            <input type="number" class="form-control" id="edit_estimated_occupancy" name="estimated_occupancy" value="${data.estimated_occupancy}" min="0" max="100" step="0.01" required>
                        </div>
                        <div class="form-group mb-3">
                            <label for="edit_estimated_average_rate">Estimated Average Rate</label>
                            <div class="input-group">
                                <span class="input-group-text">EGP</span>
                                <input type="number" class="form-control" id="edit_estimated_average_rate" name="estimated_average_rate" value="${data.estimated_average_rate}" min="0" step="0.01" required>
                            </div>
                        </div>
                        <div class="form-group mb-3">
                            <label for="edit_competitor_notes">Notes</label>
                            <textarea class="form-control" id="edit_competitor_notes" name="notes" rows="3">${data.notes || ''}</textarea>
                        </div>
                    `;
                    editCompetitorModal.show();
                })
                .catch(error => {
                    console.error('Error fetching competitor data:', error);
                    alert('Error loading competitor data. Please try again.');
                });
        });
    });

    // Delete Data Handling
    document.querySelectorAll('.delete-hotel-data, .delete-competitor-data').forEach(button => {
        button.addEventListener('click', function() {
            const dataId = this.dataset.id;
            const isHotelData = this.classList.contains('delete-hotel-data');
            
            document.getElementById('deleteAction').value = isHotelData ? 'delete_hotel_data' : 'delete_competitor_data';
            document.getElementById('deleteDataId').value = dataId;
            deleteConfirmModal.show();
        });
    });

    // Form Validation
    const validateForm = (form) => {
        const inputs = form.querySelectorAll('input[required], select[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
                input.classList.add('is-invalid');
            } else {
                input.classList.remove('is-invalid');
            }
        });
        
        return isValid;
    };

    // Add form validation to all forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });

    // Date range filter validation
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');

    if (startDateInput && endDateInput) {
        endDateInput.addEventListener('change', function() {
            if (startDateInput.value && this.value < startDateInput.value) {
                alert('End date must be after start date');
                this.value = startDateInput.value;
            }
        });

        startDateInput.addEventListener('change', function() {
            if (endDateInput.value && this.value > endDateInput.value) {
                alert('Start date must be before end date');
                this.value = endDateInput.value;
            }
        });
    }
});