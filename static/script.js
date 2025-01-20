let offset = 0;
const limit = 10;
const filters = {};

// Konwersja daty na czytelny format
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Funkcja ładująca dane do tabeli z backendu
function loadData() {
    const filterParams = Object.keys(filters)
        .map(key => `${key}=${filters[key]}`)
        .join('&');
    const url = `/api/data?offset=${offset}&limit=${limit}&${filterParams}`;
    
    $.getJSON(url, function(data) {
        const tbody = $("#reports-table tbody");
        tbody.empty();

        data.forEach(row => {
            const tr = $("<tr></tr>");
            Object.keys(row).forEach(key => {
                let cellValue = row[key];
                if (key === 'date_begin' || key === 'date_end') {
                    cellValue = formatDate(cellValue);
                }
                tr.append($("<td></td>").text(cellValue));
            });
            tbody.append(tr);
        });
    });
}

// Obsługa filtrowania
$(".filter-input").on("input", function() {
    const column = $(this).data("column");
    const value = $(this).val();
    if (value) {
        filters[column] = value;
    } else {
        delete filters[column];
    }
    offset = 0; // Resetujemy offset przy zmianie filtrów
    loadData();
});

// Obsługa przycisków paginacji
$("#prev-page").click(function() {
    if (offset > 0) {
        offset -= limit;
        loadData();
    }
});

$("#next-page").click(function() {
    offset += limit;
    loadData();
});

// Uruchomienie ładowania danych, gdy DOM jest gotowy
$(document).ready(function() {
    loadData();
});
