$(document).ready(function() {

    // All tables are initialized with sorting disabled to prevent conflict with
    //      the server-side ordering of objects

    // Initialize paged tables with default options
    $('.paged-table').DataTable({ordering: false});
    // Initialize non-paged tables without paging (obviously) and searching
    $('.non-paged-table').DataTable({
        ordering: false,
        paging: false,
        searching: false
    });
    // Obtain API handle
    var tableApi = $('.paged-table, .non-paged-table').DataTable();
    function checkboxUpdate(checkbox, table) {
        // Identify the "Status" column
        var statusIndex = $(table.table().header())
            .children().children(':contains(Status)').index();
        // Select rows where "Status" is "Unconfirmed" and get nodes as jQuery objects
        var unconfirmedRows = table
        .rows(function(index, data, node) {
            return data[statusIndex] == "Unconfirmed";
        })
        .nodes()
        .to$();
        // Show/Hide rows accoringly
        if (checkbox.checked) {
            unconfirmedRows.show();
        }
        else {
            unconfirmedRows.hide();
        }
    }
    var checkbox = $('#check-include-unconfirmed');
    checkboxUpdate(checkbox, tableApi); // Update table to match checkbox state
    checkbox.change(function() { checkboxUpdate(this, tableApi); });
});