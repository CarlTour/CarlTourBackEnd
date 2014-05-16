$(document).ready(function() {
    $('.new_alias_submit').click(function () {
        var new_alias_cell = $(this).siblings(".new_alias_text");
        var new_alias = new_alias_cell.val();
        var parent = $(this).parent();

        var old_location_cell = parent.siblings(".building_cell");
        var old_location = old_location_cell.text();

        var new_location_cell = parent.siblings(".new_building_cell");
        var new_location = new_location_cell.children(".new_building_select").val();
        
        var locationUpdates = {
            'old_location' : old_location,
            'new_location' : new_location,
            'new_alias' : new_alias
        };
        console.log(locationUpdates);

        $.post('update_building', locationUpdates, function(data) {
            // highlight this row, or something
            // actually, update all the rows with the same old_location
            old_location_cell.text(new_location);
            new_alias_cell.text('');
            console.log('all done!');
        });
    });
});