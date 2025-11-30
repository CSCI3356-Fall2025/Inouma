// Toggle Team Member fields visibility based on role selection
(function($) {
    $(document).ready(function() {
        var roleField = $('#id_role');
        var teamLeadField = $('#id_is_team_lead').closest('.form-row');
        var trainerField = $('#id_is_trainer').closest('.form-row');
        var teamAssignmentField = $('#id_team_assignment').closest('.form-row');
        
        // Also try fieldset approach
        var teamMemberFieldset = $('fieldset').filter(function() {
            return $(this).find('h2').text().includes('Team Member Settings');
        });
        
        function toggleTeamMemberFields() {
            var role = roleField.val();
            var isTeamMember = (role === 'Team Member');
            
            // Toggle individual fields
            if (teamLeadField.length) teamLeadField.toggle(isTeamMember);
            if (trainerField.length) trainerField.toggle(isTeamMember);
            if (teamAssignmentField.length) teamAssignmentField.toggle(isTeamMember);
            
            // Toggle entire fieldset
            if (teamMemberFieldset.length) {
                teamMemberFieldset.toggle(isTeamMember);
            }
            
            // If not team member, clear the values
            if (!isTeamMember) {
                $('#id_is_team_lead').prop('checked', false);
                $('#id_is_trainer').prop('checked', false);
                $('#id_team_assignment').val('');
            }
        }
        
        // Handle team lead checkbox - auto-check trainer and require team assignment
        function handleTeamLeadChange() {
            var isTeamLead = $('#id_is_team_lead').is(':checked');
            
            if (isTeamLead) {
                // Team leads are automatically trainers
                $('#id_is_trainer').prop('checked', true).prop('disabled', true);
                
                // Highlight team assignment as required
                $('#id_team_assignment').css({
                    'border-color': '#f0523e',
                    'background-color': '#fff5f5'
                });
                
                // Add required indicator if not present
                var label = $('label[for="id_team_assignment"]');
                if (!label.find('.required-indicator').length) {
                    label.append('<span class="required-indicator" style="color: #f0523e; margin-left: 4px;">*</span>');
                }
            } else {
                // Re-enable trainer checkbox
                $('#id_is_trainer').prop('disabled', false);
                
                // Remove required styling
                $('#id_team_assignment').css({
                    'border-color': '',
                    'background-color': ''
                });
                
                // Remove required indicator
                $('label[for="id_team_assignment"] .required-indicator').remove();
            }
        }
        
        // Validate before form submit
        $('form').on('submit', function(e) {
            var isTeamLead = $('#id_is_team_lead').is(':checked');
            var teamAssignment = $('#id_team_assignment').val();
            
            if (isTeamLead && !teamAssignment) {
                e.preventDefault();
                alert('Team assignment is required for team leads.');
                $('#id_team_assignment').focus();
                return false;
            }
        });
        
        // Bind events
        roleField.on('change', toggleTeamMemberFields);
        $('#id_is_team_lead').on('change', handleTeamLeadChange);
        
        // Initial state
        toggleTeamMemberFields();
        handleTeamLeadChange();
    });
})(django.jQuery);