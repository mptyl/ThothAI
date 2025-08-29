// Initialize DataTable with proper sorting configuration
$("#questions-datatable").DataTable({
    language: {
        paginate: {
            previous: "<i class='mdi mdi-chevron-left'>",
            next: "<i class='mdi mdi-chevron-right'>"
        },
        info: "Showing questions _START_ to _END_ of _TOTAL_",
        lengthMenu: 'Display <select class=\'form-select form-select-sm ms-1 me-1\'><option value="5">5</option><option value="10">10</option><option value="15">15</option><option value="20">20</option><option value="-1">All</option></select> questions'
    },
    pageLength: 15,
    order: [[0, 'asc']],
    columnDefs: [
        { orderData: [0,], targets: 0 },
        { orderData: [1,], targets: 1 },
        {
            targets: 2, // Indice della colonna "Action" (0-based)
            width: "45px",
            className: "action-column"
        },
        { orderable: false, targets: -1 } // Ultima colonna non ordinabile
    ],
    drawCallback: function() {
        $(".dataTables_paginate > .pagination").addClass("pagination-rounded");
    }
});
