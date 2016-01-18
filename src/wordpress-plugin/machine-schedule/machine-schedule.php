<?php
/*
Plugin Name: FabLab Luxembourg Machine Use Schedule
Description: Add a live view of the machine use schedule to a page.
Author: Alexandre Saint
Version: 1.0
*/

defined('ABSPATH') or exit; 

/**
 * Manage the options for the machine use schedule.
 */
class MachineScheduleOptions implements ArrayAccess {

    /**
     * Name of the option key.
     */
    const storage_name = "machine_use";

    /**
     * Unique id of the admin menu for managing the plugin options.
     */
    private $admin_menu_slug = self::prefix . '-admin_menu';

    /**
     * The default options array.
     */
    private static $default_options = array(
        "page_title" => "",
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
        $field_page_title = 'machine_page_title';
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
            $page_title = $_POST[$field_page_title];
            $machine_names = $_POST[$field_machine_names];
            $slot_names = $_POST[$field_slot_names];
            $opening_hours = $_POST[$field_opening_hours];
            $timezone = $_POST[$field_timezone];

            $this['page_title'] = $page_title;
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
        $page_title = $this['page_title'];
        $page_titles_html = "";
        foreach(get_pages() as $page) {
            $title = $page->post_title;
            if ($title == $page_title) {
                $page_titles_html .= "<option value='$title'" .
                                     " selected='selected'>$title</option>";
            } else {
                $page_titles_html .= "<option value='$title'>$title</option>";
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
<h1>Machine Use Schedule Options</h1>
<form name="machine-use-schedule-options" method="post" action="">
<input type="hidden" name="$field_action" value="update">

<table class="form-table">

<tr>
<th scope="row"><label for="$field_page_title">Target page:</label></th>
<td>
<select name="$field_page_title">
    <option value='' default></option>
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
<th scope="row"><label for="$field_timezone">Timezone:</label></th>
<td>
<select name="$field_timezone">
    $timezone_html_options
</select>
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


/**
 * Display the machine use schedule during open access time.
 *
 * TODO:
 *
 * - Record and display a timestamp of the table update.
 * - Give the possibility to hide some rows/columns from the admin panel.
 * - Make the wordpress cookie authentication work.
 *   Probably requires the use of nonces with action 'wp_json'. Create the
 *   nonce on the server with wp_create_nonce('wp_json'). Pass it along to
 *   the client somehow. The client includes the header 'X-WP-Nonce' with the
 *   value of the nonce in every header.
 *
 * History:
 * - Add the timezone of the opening hours as an option.
 * - Display the table only during opening hours.
 * - Add the opening hours as an option.
 * - Add the table header labels as options.
 * - Expose the options in the administration panel.
 * - Prefix the custom metadata keys.
 * - Change const arrays inside the class to private static prorperties for
 *   earlier PHP version support.
 */
class Fablab_MachineSchedule {

    /**
     * The singleton instance of this class.
     *
     * $var Fablab_MachineSchedule $instance
     */
    static $instance = false;

    /**
     * Prefix of the metadata.
     *
     * $var string $prefix
     */
    const prefix = 'machine_schedule_';

    /**
     * The key of the metadata used to store the table.
     *
     * $var string $meta_table
     */
    private $meta_table = self::prefix . 'table';

    /**
     * Unique id of the admin menu for managing the plugin options.
     */
    private $admin_menu_slug = self::prefix . '-admin_menu';

    /**
     * The options array.
     */
    private $options = null;

    /**
     * Constructor.
     *
     * Register hooks.
     */
    private function __construct() {
        register_activation_hook(
            __FILE__,
            array('Fablab_MachineSchedule', 'activate')
        );
        register_uninstall_hook(
            __FILE__,
            array('Fablab_MachineSchedule', 'uninstall')
        );
        add_action('admin_menu', array($this, 'admin_menu'));
        add_filter('the_content', array($this, 'the_content'), 20, 1);
        $this->api_register_routes();

        $this->options = new MachineScheduleOptions();
    } 

    /**
     * Get the singleton instance of this class.
     *
     * The instance is created if it does not exist yet.
     *
     * @return Fablab_MachineSchedule
     */
    public static function instance() {
        if (!self::$instance) {
            self::$instance = new self;
        }
        return self::$instance;
    }

    /**
     * Set up the plugin on activation.
     */
    public static function activate() {
        if (!current_user_can('activate_plugins')) {
            return;
        }
        // This calls initialises the options in the database.
        $options = new MachineScheduleOptions();
    }

    /**
     * Clear plugin data on uninstallation.
     */
    public static function uninstall() {
        if (!current_user_can('activate_plugins')) {
            return;
        }
        $options = new MachineScheduleOptions();
        $options->delete();
    }

    /**
     * Add an options page in the admin menu.
     */
    public function admin_menu() {
        /*
        add_options_page('Machine Use Schedule Options',
                         'Machine Use Schedule',
                         'manage_options',
                         $this->admin_menu_slug,
                         array($this, 'render_options'));
         */
        add_options_page('Machine Use Schedule Options',
                         'Machine Use Schedule',
                         'manage_options',
                         $this->admin_menu_slug,
                         array($this->options, 'render_options'));
    }

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
     *
     * @return string
     */
    public function render_options() {
        if (!current_user_can('manage_options')) {
            wp_die(('You do not have sufficient permissions to access this' .
                    ' page.'));
        }

        // Define unique field names for the form inputs.
        $field_action = 'machine_action';
        $field_page_title = 'machine_page_title';
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
            $page_title = $_POST[$field_page_title];
            $machine_names = $_POST[$field_machine_names];
            $slot_names = $_POST[$field_slot_names];
            $opening_hours = $_POST[$field_opening_hours];
            $timezone = $_POST[$field_timezone];

            $this->options['page_title'] = $page_title;
            $this->options['machine_names'] = explode("\n", $machine_names);
            $this->options['slot_names'] = explode("\n", $slot_names);
            $hours_array = $this->parse_opening_hours($opening_hours);
            $this->options['opening_hours'] = $hours_array;
            $this->options['timezone'] = $timezone;

            $this->options->save();

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
            $this->options->reset();
            $this->options->save();
            $message = "<div><p><strong>Options reset!</strong></p></div>";
            echo($message);
        }

        // Retrieve option values.
        $page_title = $this->options['page_title'];
        $page_titles_html = "";
        foreach(get_pages() as $page) {
            $title = $page->post_title;
            if ($title == $page_title) {
                $page_titles_html .= "<option value='$title'" .
                                     " selected='selected'>$title</option>";
            } else {
                $page_titles_html .= "<option value='$title'>$title</option>";
            }
        }
        $machine_names = $this->options['machine_names'];
        $machine_names_string = join("\n", $machine_names);
        $slot_names = $this->options['slot_names'];
        $slot_names_string = join("\n", $slot_names);
        $hours = $this->options['opening_hours'];
        $opening_hours_string = $this->format_opening_hours($hours);
        $current_timezone = $this->options['timezone'];
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
<h1>Machine Use Schedule Options</h1>
<form name="machine-use-schedule-options" method="post" action="">
<input type="hidden" name="$field_action" value="update">

<table class="form-table">

<tr>
<th scope="row"><label for="$field_page_title">Target page:</label></th>
<td>
<select name="$field_page_title">
    <option value='' default></option>
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
<th scope="row"><label for="$field_timezone">Timezone:</label></th>
<td>
<select name="$field_timezone">
    $timezone_html_options
</select>
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

    /**
     * Get the status of the open access.
     *
     * @return bool True if open, false otherwise.
     */
    private function is_open() {
        $timezone = new DateTimeZone($this->options['timezone']);
        $local_date = new DateTime("now", $timezone);
        $timestamp = $local_date->getTimestamp() + $local_date->getOffset();
        $now = getdate($timestamp);
        $opening_hours = $this->options['opening_hours'];
        foreach($opening_hours as $slot) {
            // Invalid data
            // Need (day, start_hour, start_min, end_hour, end_min).
            if (count($slot) != 5) {
                continue;
            }
            list($day, $start_h, $start_m, $end_h, $end_m) = $slot;
            $day_match = $now['weekday'] === $day;
            $past_start_hour = $now['hours'] > $start_h ||
                               ($now['hours'] == $start_h &&
                                $now['minutes'] >= $start_m);
            $before_end_hour = $now['hours'] < $end_h ||
                               ($now['hours'] == $end_h &&
                                $now['minutes'] < $end_m);
            if ($day_match && $past_start_hour && $before_end_hour) {
                return true;
            }
        }
        return false;
    }

    /**
     * Get the ID of the open access page.
     *
     * @return int
     */
    private function get_page_id() {
        $page = get_page_by_title($this->options['page_title']);
        if (!is_null($page)) {
            return $page->ID;
        }
        return null;
    }

    /**
     * Get the machine schedule as an array of bool.
     *
     * Return the value of json_decode.
     *
     * @see json_decode
     * @return mixed Array or null if the array cannot be decoded from JSON.
     */
    private function get_table() {
        $page_id = $this->get_page_id();
        $single = true;
        $table_json = get_post_meta($page_id, $this->meta_table, $single);
        $table = json_decode($table_json);
        return $table;
    }

    /**
     * Update the occupation table.
     *
     * @param array $table Array of bool.
     */
    private function update_table($table) {
        $page_id = $this->get_page_id();
        update_post_meta($page_id, $this->meta_table, json_encode($table));
    }

    /**
     * Display the machine occupation table at the end of the content.
     *
     * @param string $content The original content.
     * @return string The modified content.
     */
    public function the_content($content) {
        if (!is_page($this->options['page_title'])) {
            return $content;
        }

        // TODO: Should we display something when the open access is off,
        //       like a "Closed" message?
        if (!$this->is_open()) {
            return $content;
        }

        // Get the occupation table data.
        $table = $this->get_table();
        $machine_names = $this->options['machine_names'];
        $slot_names = $this->options['slot_names'];

        // Exit early if no data to display.
        if (is_null($table)) {
            return $content;
        }

        // Display the table.
        $table_html = '<h2>Machine Occupation</h2>';
        $table_html .= '<table class="occupation-table"' .
            ' style="border: none; border-spacing: 0.5em;">';
        $table_html .= '<tr style="border: none;">';
        $table_html .= '<td style="border: none; width: 20%"></td>';
        foreach($slot_names as $slot_name) {
            $table_html .= "<th style='border: none;'>$slot_name</th>";
        }
        $table_html .= '</tr>';
        foreach($table as $machine_index => $slots) {
            $table_html .= '<tr style="padding: 1em;">';
            $machine_name = $machine_names[$machine_index];
            $table_html .= "<th style='border: none;'>$machine_name</th>";
            foreach($slots as $occupied) {
                if ($occupied) {
                    $class = '';
                    $style = 'background-color: #f78181;';   // red
                } else {
                    $class = '';
                    $style = 'background-color: #81f781;';   // green
                }
                $style .= 'border: none;';
                $table_html .= "<td class='$class' style='$style'></td>";
            }
            $table_html .= '</tr>';
            $machine_index++;
        }
        $table_html .= '</table>';

        $content = $table_html . $content;

        return $content;
    }

    // -----------------------------------------------------------------------
    // REST API 
    // -----------------------------------------------------------------------

    /**
     * Register the API endpoints.
     */
    private function api_register_routes() {
        add_action('rest_api_init', function() {
            register_rest_route('open-access/v1', '/', array(
                'methods' => 'GET',
                'callback' => array($this, 'api_get_status'),
            ));
            register_rest_route('open-access/v1', '/occupation', array(
                'methods' => 'GET',
                'callback' => array($this, 'api_get_occupation'),
                'permission_callback' => array($this, 'api_authenticate'),
            ));
            register_rest_route('open-access/v1', '/occupation', array(
                'methods' => 'POST',
                'callback' => array($this, 'api_update_occupation'),
                'args' => array(
                    'table' => array(
                        'required' => true,
                    ),
                ),
                'permission_callback' => array($this, 'api_authenticate'),
            ));
        });
    }

    /**
     * Authenticate the user from a REST request.
     *
     * @param WP_REST_Request $request The REST request containing the
     *                                 'username' and 'password' fields.
     *
     * @return bool true on success, false otherwise.
     */
    public function api_authenticate(WP_REST_Request $request) {
        // TODO: Make use of a nonce?
        $username = $request['username'];
        $password = $request['password'];
        $credentials = array(
            'user_login' => $username,
            'user_password' => $password,
            'remember' => false,
        );
        $securecookie = false;
        $user = wp_signon($credentials, $securecookie);
        return !is_wp_error($user);
    }

    /**
     * Get the status of the open access as a JSON string.
     *
     * The JSON message has the following structure:
     *
     *    {
     *      "open": true|false
     *    }
     *
     * @return string
     */
    public function api_get_status() {
        $data = array(
            'open' => $this->is_open(),
        );
        return json_encode($data);
    }

    /**
     * Get the occupation table as a JSON string.
     *
     * The JSON is has the following structure:
     *
     *    {
     *      "table": [
     *                [true, false, ..., false],
     *                [false, true, ..., true],
     *                ...,
     *                [false, true, ..., false]
     *               ]
     *    }
     *
     * @return string
     */
    public function api_get_occupation() {
        $table = $this->get_table();
        $data = array(
            'table' => $table,
        );
        return json_encode($data);
    }

    /**
     * Update the occupation table.
     *
     * @param WP_REST_Request $request The REST API request.
     * @return 
     */
    public function api_update_occupation(WP_REST_Request $request) {
        $table = $request['table'];
        $this->update_table($table);
        $data = array(
            'code' => 'updated',
            'message' => 'Occupation table successfully updated.',
            'data' => array(
                'table' => $table,
            ),
        );
        return json_encode($data);
    }
}

$open_access = Fablab_MachineSchedule::instance();
?>
