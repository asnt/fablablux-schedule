<?php

/**
 * Manage the options for the machine schedule.
 */
class MachineScheduleOptions implements ArrayAccess {

    /**
     * Name of the option key.
     */
    const storage_name = "machine_schedule";

    /**
     * The default options array.
     */
    private static $default_options = array(
        "page_id" => -1,
        "machine_names" => array("MakerBot 1", "MakerBot 2", "RepRap",
                                 "Small CNC", "Big CNC", "Laser Cutter",
                                 "Vinyl Cutter"),
        "slot_names" => array("14:00", "15:00", "16:00", "17:00", "18:00",
                              "19:00", "20:00", "21:00", "22:00"),
        "opening_hours" => array(
            // (day, start_hour, start_minutes, end_hour, end_minutes)
            array("Thursday", 14, 0, 21, 0),
        ),
        "timezone" => "Europe/Luxembourg",
    );

    /**
     * The options array.
     */
    private $options = null;

    /**
     * Indicate if the options have already been loaded from the database.
     */
    private $loaded = false;

    public function __construct() {
        $this->init();
    }

    /**
     * Load the options or create default ones if they do not yet exist.
     */
    private function init() {
        if (!$this->load()) {
            $this->reset();
            $this->save();
        }
    }

    /**
     * Load the options from the database.
     *
     * @return bool True on success, false if the option does not exist.
     */
    private function load() {
        $options = get_option(self::storage_name);
        if ($options == false) {
            return false;
        } else {
            $this->options = $options;
            return true;
        }
    }

    /**
     * Save the options in the database.
     */
    public function save() {
        update_option(self::storage_name, $this->options);
    }

    /**
     * Delete the options from the database.
     */
    public function delete() {
        delete_option(self::storage_name);
    }

    /**
     * Reset the default options.
     */
    public function reset() {
        $this->options = self::$default_options;
    }

    /**
     * Get the title of the currently defined page ID.
     */
    public function get_page_title() {
        $page_id = $this['page_id'];
        if (!is_page($page_id)) {
            return "";
        }
        return get_the_title($page_id);
    }

    //----------------------
    // ArrayAccess interface
    //----------------------

    /**
     */
    public function offsetSet($offset, $value) {
        if(is_null($offset)) {
            $this->options[] = $value;
        } else {
            $this->options[$offset] = $value;
        }
    }

    /**
     */
    public function offsetExists($offset) {
        return isset($this->options[$offset]);
    }

    /**
     */
    public function offsetUnset($offset) {
        unset($this->options[$offset]);
    }

    /**
     */
    public function offsetGet($offset) {
        if (isset($this->options[$offset])) {
            return $this->options[$offset];
        } else {
            return null;
        }
    }

    //---------------------------------
    // Rendering of options admin menu.
    //---------------------------------

    /**
     * Parse the textfield of opening hours.
     *
     * @return array
     */
    private function parse_opening_hours($string) {
        $opening_hours = array();
        $entries = explode("\n", $string);
        foreach($entries as $entry) {
            $tokens = explode(" ", $entry);
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
    private function format_opening_hours($opening_hours) {
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

    /**
     * Render the HTML of the options menu.
     */
    public function render_admin_menu() {
        if (!current_user_can('manage_options')) {
            wp_die(('You do not have sufficient permissions to access this' .
                    ' page.'));
        }

        // Define unique field names for the form inputs.
        $field_action = 'machine_action';
        $field_page_id = 'machine_page_id';
        $field_machine_names = 'machine_machine_names';
        $field_slot_names = 'machine_slot_names';
        $field_opening_hours = 'machine_opening_hours';
        $field_timezone = 'machine_timezone';

        // Save changes if this is a POST request.
        if (isset($_POST[$field_action])) {
            $action = $_POST[$field_action];
        } else {
            $action = "";
        }
        if ($action == "update") {
            $page_id = intval($_POST[$field_page_id]);
            $machine_names = $_POST[$field_machine_names];
            $slot_names = $_POST[$field_slot_names];
            $opening_hours = $_POST[$field_opening_hours];
            $timezone = $_POST[$field_timezone];

            $this['page_id'] = $page_id;
            $this['machine_names'] = explode("\n", $machine_names);
            $this['slot_names'] = explode("\n", $slot_names);
            $hours_array = $this->parse_opening_hours($opening_hours);
            $this['opening_hours'] = $hours_array;
            $this['timezone'] = $timezone;

            $this->save();

            $message = "<div><p><strong>Changes saved!</strong></p></div>";
            echo($message);
        } else if ($action == "reset") {
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
<input type="hidden" name="$field_action" value="confirm-reset">
<input type="submit" name="button-confirm-reset" value="Yes, reset"
       class="button button-primary">
<input type="submit" name="button-cancel-reset" value="No, cancel"
       class="button button-primary">
</form>
END;
            echo($confirmation_form);
            return;
        } else if ($action == 'confirm-reset' &&
                   isset($_POST['button-confirm-reset'])) {
            $this->reset();
            $this->save();
            $message = "<div><p><strong>Options reset!</strong></p></div>";
            echo($message);
        }

        // Retrieve option values.
        $page_id = $this['page_id'];
        $page_titles_html = "";
        foreach(get_pages() as $page) {
            $title = $page->post_title;
            $id = $page->ID;
            if ($id == $page_id) {
                $page_titles_html .= "<option value='$id'" .
                                     " selected='selected'>$title</option>";
            } else {
                $page_titles_html .= "<option value='$id'>$title</option>";
            }
        }
        $machine_names = $this['machine_names'];
        $machine_names_string = join("\n", $machine_names);
        $slot_names = $this['slot_names'];
        $slot_names_string = join("\n", $slot_names);
        $hours = $this['opening_hours'];
        $opening_hours_string = $this->format_opening_hours($hours);
        $current_timezone = $this['timezone'];
        $timezone_html_options = "";
        foreach(DateTimeZone::listIdentifiers() as $timezone) {
            if ($timezone == $current_timezone) {
                $string = "<option name='$field_timezone' value='$timezone'"
                          . " selected='selected'>$timezone</option>";
            } else {
                $string = "<option name='$field_timezone' value='$timezone'>"
                          . "$timezone</option>";
            }
            $timezone_html_options .= $string;
        }

        // Render the HTML form.
        $form = <<<END
<div class="wrap">
<h1>Machine Schedule Options</h1>
<form name="machine-use-schedule-options" method="post" action="">
<input type="hidden" name="$field_action" value="update">

<table class="form-table">

<tr>
<th scope="row"><label for="$field_page_id">Target page:</label></th>
<td>
<select name="$field_page_id">
    <option value='-1' default></option>
    $page_titles_html
</select>
<p class="description">The page where to display the machine use schedule.</p>
<p class="description">If blank, the schedule will not be displayed.</p>
</td>
</tr>

<tr>
<th scope="row"><label for="$field_machine_names">Machines names:</label></th>
<td>
<textarea name="$field_machine_names"
          rows="7" cols="15">$machine_names_string</textarea>
<p class="description">The header column of the table.</p>
<p class="description">Put one machine per line.</p>
</td>
</tr>

<tr>
<th scope="row"><label for="$field_slot_names">Time slots names:</label></th>
<td>
<textarea name="$field_slot_names"
          rows="9" cols="15">$slot_names_string</textarea>
<p class="description">The header row of the table.</p>
<p class="description">Put one slot per line.</p>
</td>
</tr>

<tr>
<th scope="row"><label for="$field_opening_hours">Opening hours:</label></th>
<td>
<textarea name="$field_opening_hours"
          rows="5" cols="15">$opening_hours_string</textarea>
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
<th scope="row"><label for="$field_timezone">Time zone:</label></th>
<td>
<select name="$field_timezone">
    $timezone_html_options
</select>
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
<input type="hidden" name="$field_action" value="reset">
<input type="submit" name="submit" value="Reset default options"
       class="button button-secondary">
</form>
</div>
END;
        echo($form);
    }
}

?>

