document.addEventListener('DOMContentLoaded', () => {
    const noteForm = document.getElementById('note-form');
    const noteInput = document.getElementById('note-input');
    const notesContainer = document.getElementById('notes-container');

    // Load notes from local storage
    loadNotes();

    noteForm.addEventListener('submit', (e) => {
        e.preventDefault();
        addNote();
    });

    function loadNotes() {
        const notes = getNotesFromStorage();
        notes.forEach(noteText => {
            displayNote(noteText);
        });
    }

    function getNotesFromStorage() {
        const notes = localStorage.getItem('ideaPadNotes');
        return notes ? JSON.parse(notes) : [];
    }

    function saveNotesToStorage(notes) {
        localStorage.setItem('ideaPadNotes', JSON.stringify(notes));
    }

    function addNote() {
        const noteText = noteInput.value.trim();
        if (noteText === '') {
            // Maybe show an alert or some UI feedback
            return;
        }

        const notes = getNotesFromStorage();
        notes.push(noteText);
        saveNotesToStorage(notes);

        displayNote(noteText);
        noteInput.value = ''; // Clear textarea
    }

    function displayNote(noteText) {
        const noteElement = document.createElement('div');
        noteElement.classList.add('note');
        noteElement.textContent = noteText;

        // Add to the top of the list (newest first)
        notesContainer.insertBefore(noteElement, notesContainer.firstChild);
    }

    // Optional: Add a function to clear all notes (for testing or user feature)
    // function clearAllNotes() {
    //     localStorage.removeItem('ideaPadNotes');
    //     notesContainer.innerHTML = ''; // Clear display
    // }
    // Example: You could hook this to a button:
    // const clearButton = document.getElementById('clear-all-button');
    // if(clearButton) clearButton.addEventListener('click', clearAllNotes);
});
