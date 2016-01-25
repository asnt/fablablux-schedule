<?php

include_once(plugin_dir_path(__FILE__) . 'options.php');

class OptionsView {

    // Unique names for the form inputs.
    private static $input_names = array(
        "action" => "machine_action",
        "machine_name" => "machine_machine_name",
        "slot_name" => "machine_slot_name",
        "machine_visible" => "machine_machine_visible",
        "slot_visible" => "machine_slot_visible",
        "opening_hours" => "machine_opening_hours",
        "timezone" => "machine_timezone",
    );

    public static function render() {
        $options = MachineScheduleOptions::instance();
        $input_names = self::$input_names;

        if (isset($_POST[$input_names['action']])) {
            $action = $_POST[$input_names['action']];
        } else {
            $action = "";
        }

        // Save changes if this is a POST request.
        if ($action == "update") {
            $new_options = OptionsView::get_values();

            $options['machine_names'] = $new_options['machine_names'];
            $options['slot_names'] = $new_options['slot_names'];
            $options['visible_machines'] = $new_options['visible_machines'];
            $options['visible_slots'] = $new_options['visible_slots'];
            $options['opening_hours'] = $new_options['opening_hours'];
            $options['timezone'] = $new_options['timezone'];

            $options->save();

            $message = "<div><p><strong>Changes saved!</strong></p></div>";
            echo($message);
        // Ask confirmation before reset.
        } else if ($action == "reset") {
            echo(self::render_confirmation());
            return;
        // Do the reset.
        } else if ($action == 'confirm-reset' &&
                   isset($_POST['button-confirm-reset'])) {
            $options->reset();
            $options->save();
            $message = "<div><p><strong>Options reset!</strong></p></div>";
            echo($message);
        }

        $current_timezone = $options['timezone'];        
        $opening_hours = $options['opening_hours'];        
        $inputs = array(
            "machines" => self::render_machines(),
            "timeslots" => self::render_timeslots(),
            "opening_hours" => self::render_opening_hours($opening_hours),
            "timezone" => self::render_timezone($current_timezone),
        );
        $form = self::render_form($inputs);

        echo($form);
    }

    public static function render_confirmation() {
        $input_names = self::$input_names;

        $confirmation_form = <<<END
<div>
<p>
You are about to reset the default options of the machine use schedule plugin.
All your changes will be <strong>permanently</strong> deleted.
</p>
<p>
Are you sure you want to proceed?
</p>
</div>
<form name="machine-use-schedule-reset" method="post" action="">
<input type="hidden" name="${input_names['action']}" value="confirm-reset">
<input type="submit" name="button-confirm-reset" value="Yes, reset"
       class="button button-primary">
<input type="submit" name="button-cancel-reset" value="No, cancel"
       class="button button-primary">
</form>
END;

        return $confirmation_form;
    }

    private static function get_values() {
        $options = MachineScheduleOptions::instance();
        $input_names = self::$input_names;

        $opening_hours = $_POST[$input_names['opening_hours']];
        $timezone = $_POST[$input_names['timezone']];

        $n_machines = count($options['machine_names']);

        $machine_names = array();
        for($index = 0; $index < $n_machines; $index++) {
            $input_name = "${input_names['machine_name']}_${index}";
            $name = $_POST[$input_name];
            array_push($machine_names, $name); 
        }

        $visible_machines = array();
        for($index = 0; $index < $n_machines; $index++) {
            $input_name = "${input_names['machine_visible']}_${index}";
            if (isset($_POST[$input_name])) {
                $visible = true;
            } else {
                $visible = false;
            }
            array_push($visible_machines, $visible); 
        }

        $n_slots = count($options['slot_names']);

        $slot_names = array();
        for($index = 0; $index < $n_slots; $index++) {
            $input_name = "${input_names['slot_name']}_${index}";
            $name = $_POST[$input_name];
            array_push($slot_names, $name); 
        }

        $visible_slots = array();
        for($index = 0; $index < $n_slots; $index++) {
            $input_name = "${input_names['slot_visible']}_${index}";
            if (isset($_POST[$input_name])) {
                $visible = true;
            } else {
                $visible = false;
            }
            array_push($visible_slots, $visible); 
        }

        $values = array();
        $values['machine_names'] = $machine_names;
        $values['slot_names'] = $slot_names;
        $values['visible_machines'] = $visible_machines;
        $values['visible_slots'] = $visible_slots;
        $hours_array = self::parse_opening_hours($opening_hours);
        $values['opening_hours'] = $hours_array;
        $values['timezone'] = $timezone;

        return $values;
    }

    /**
     * Render inputs to modify the machine names and their visibility.
     *
     * @return string
     */
    private static function render_machines() {
        $options = MachineScheduleOptions::instance();
        $input_names = self::$input_names;

        $machine_names = $options['machine_names'];
        $visible_machines = $options['visible_machines'];

        $html = "";
        for($index = 0; $index < count($machine_names); $index++) {
            $name = $machine_names[$index];
            $visible = $visible_machines[$index] ? "checked='checked'" : "";

            $html .= "<div>";
            $html .= "<input type='text'" .
                           " name='${input_names['machine_name']}_${index}'" .
                           " value='$name'>";
            $html .= "<input type='checkbox'" .
                           " name='${input_names['machine_visible']}_${index}'" .
                           " $visible>";
            $html .= "</div>";
        }

        return $html;
    }

    /**
     * Render inputs to modify the slot names and their visibility.
     *
     * @return string
     */
    private static function render_timeslots() {
        $options = MachineScheduleOptions::instance();
        $input_names = self::$input_names;

        $slot_names = $options['slot_names'];
        $visible_slots = $options['visible_slots'];

        $html = "";
        for($index = 0; $index < count($slot_names); $index++) {
            $name = $slot_names[$index];
            $visible = $visible_slots[$index] ? "checked='checked'" : "";
            $html .= "<div>";
            $html .= "<input type='text'" .
                           " name='${input_names['slot_name']}_${index}'" .
                           " value='$name'>";
            $html .= "<input type='checkbox'" .
                           " name='${input_names['slot_visible']}_${index}'" .
                           " $visible>";
            $html .= "</div>";
        }

        return $html;
    }

    private static function render_opening_hours($opening_hours) {
        $input_names = self::$input_names;

        $html = "<textarea name='${input_names['opening_hours']}'" .
                         " rows='5' cols='15'>";
        $html .= self::format_opening_hours($opening_hours);
        $html .= "</textarea>";

        return $html;
    }

    private static function render_timezone($current_timezone) {
        $input_names = self::$input_names;

        $html = "<select name='${input_names['timezone']}'>";
        foreach(DateTimeZone::listIdentifiers() as $timezone) {
            if ($timezone == $current_timezone) {
                $html .= "<option value='$timezone'" .
                                " selected='selected'>$timezone</option>";
            } else {
                $html .= "<option value='$timezone'>$timezone</option>";
            }
        }
        $html .= "</select>";

        return $html;
    }

    /**
     * Render the options form.
     *
     * @param $inputs array() Array of the individual html inpus:
     *                        $input = array(
     *                          "page" => "...",
     *                          "machines" => "...",
     *                          "timeslots" => "...",
     *                          "opening_hours" => "...",
     *                          "timezone" = "...",
     *                        )
     * @return string
     */
    private static function render_form($inputs) {
        $input_names = self::$input_names;

        $html = <<<END
<div class="wrap">
<h1>Machine Schedule Options</h1>
<form name="machine-use-schedule-options" method="post" action="">
<input type="hidden" name="${input_names['action']}" value="update">

<table class="form-table">

<tr>
<th scope="row"><label>Machines:</label></th>
<td>
${inputs['machines']}
<p class="description">Unchecked machines are not displayed.</p>
</td>
</tr>

<tr>
<th scope="row"><label>Time slots:</label></th>
<td>
${inputs['timeslots']}
<p class="description">If unchecked, the slot is not displayed.</p>
</td>
</tr>

<tr>
<th scope="row">
<label for="${input_names['opening_hours']}">Opening hours:</label>
</th>
<td>
${inputs['opening_hours']}
<p class="description">
Determine when to display the schedule.
</p>
<p class="description">
Put one time slot per line.
</p>
<p class="description">
The format is 'day start_time end_time'. For example, 'Thursday 14:00 21:00'.
</p>
<p class="description">
The days are: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday.
</p>
</td>
</tr>

<tr>
<th scope="row">
<label for="${input_names['timezone']}">Time zone:</label>
</th>
<td>
${inputs['timezone']}
<p class="description">
Time zone of the opening hours.
</p>
</td>
</tr>

</table>

<input type="submit" name="submit" value="Save changes"
       class="button button-primary">
</form>
<br />
<form name="machine-use-schedule" method="post" action="">
<input type="hidden" name="${input_names['action']}" value="reset">
<input type="submit" name="submit" value="Reset default options"
       class="button button-secondary">
</form>
</div>
END;

        return $html;
    }

    /**
     * Parse the textfield of opening hours.
     *
     * @return array
     */
    private static function parse_opening_hours($string) {
        $opening_hours = array();
        $entries = explode("\n", $string);
        foreach($entries as $entry) {
            $entry = trim($entry);
            if ($entry == "") {
                continue;
            }

            $tokens = explode(" ", $entry);
            if (count($tokens) != 3) {
                continue;
            }

            $day = $tokens[0];
            $start = date_parse_from_format("H:i", $tokens[1]);
            $end = date_parse_from_format("H:i", $tokens[2]);
            $slot = array($day, $start['hour'], $start['minute'],
                                $end['hour'], $end['minute']);
            array_push($opening_hours, $slot);
        }
        return $opening_hours;
    }

    /**
     * Format the opening hours array for editing in a textarea.
     *
     * @return string
     */
    private static function format_opening_hours($opening_hours) {
        $entries = array();
        foreach($opening_hours as $entry) {
            if (count($entry) != 5) {
                $string = join(" ", $entry);
            } else {
                $string = sprintf("%s %02d:%02d %02d:%02d",
                                  $entry[0], $entry[1], $entry[2],
                                  $entry[3], $entry[4]);
            }
            array_push($entries, $string);
        }
        return join("\n", $entries);
    }
}

?>
