<?php
/*
Plugin Name: FabLabLux Machine Schedule
Description: Add a live view of the machine use schedule to a page.
Author: Alexandre Saint
Version: 1.0
*/

defined('ABSPATH') or exit; 

include(plugin_dir_path(__FILE__) . 'machine-schedule-api.php');
include(plugin_dir_path(__FILE__) . 'machine-schedule-options.php');

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
class MachineSchedule {

    /**
     * The singleton instance of this class.
     *
     * $var MachineSchedule $instance
     */
    static $instance = false;

    /**
     * The key of the metadata used to store the table.
     *
     * $var string $meta_table
     */
    private $meta_table = 'machine_schedule_table';

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
        $this->api = new MachineScheduleApi($this);
        $this->api->activate();
        register_activation_hook(
            __FILE__,
            array('MachineSchedule', 'activate')
        );
        register_uninstall_hook(
            __FILE__,
            array('MachineSchedule', 'uninstall')
        );
        add_action('admin_menu', array($this, 'admin_menu'));
        add_filter('the_content', array($this, 'the_content'), 20, 1);

        $this->options = new MachineScheduleOptions();
    } 

    /**
     * Get the singleton instance of this class.
     *
     * The instance is created if it does not exist yet.
     *
     * @return MachineSchedule
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
        add_options_page('Machine Schedule Options',
                         'Machine Schedule',
                         'manage_options',
                         'machine-schedule-admin-menu',
                         array($this->options, 'render_admin_menu'));
    }

    /**
     * Get the status of the open access.
     *
     * @return bool True if open, false otherwise.
     */
    public function is_open_access() {
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
    public function get_table() {
        $page_id = $this->get_page_id();
        $single = true;
        $table_json = get_post_meta($page_id, $this->meta_table, $single);
        $table = json_decode($table_json);
        return $table;
    }

    /**
     * Update the schedule table.
     *
     * @param array $table Array of bool.
     */
    public function update_table($table) {
        $page_id = $this->get_page_id();
        update_post_meta($page_id, $this->meta_table, json_encode($table));
    }

    /**
     * Display the machine schedule table at the end of the content.
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
        if (!$this->is_open_access()) {
            return $content;
        }

        // Get the schedule table data.
        $table = $this->get_table();
        $machine_names = $this->options['machine_names'];
        $slot_names = $this->options['slot_names'];

        // Exit early if no data to display.
        if (is_null($table)) {
            return $content;
        }

        // Display the table.
        $table_html = '<h2>Live Machine Use Schedule</h2>';
        $table_html .= '<table class="machine-schedule-table"' .
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
            foreach($slots as $in_use) {
                if ($in_use) {
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
            register_rest_route('open-access/v1', '/machine-schedule', array(
                'methods' => 'GET',
                'callback' => array($this, 'api_get_schedule'),
                'permission_callback' => array($this, 'api_authenticate'),
            ));
            register_rest_route('open-access/v1', '/machine-schedule', array(
                'methods' => 'POST',
                'callback' => array($this, 'api_update_schedule'),
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
     *      "open_access": true|false
     *    }
     *
     * @return string
     */
    public function api_get_status() {
        $data = array(
            'open_access' => $this->is_open_access(),
        );
        return json_encode($data);
    }

    /**
     * Get the schedule table as a JSON string.
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
    public function api_get_schedule() {
        $table = $this->get_table();
        $data = array(
            'table' => $table,
        );
        return json_encode($data);
    }

    /**
     * Update the schedule table.
     *
     * @param WP_REST_Request $request The REST API request.
     * @return 
     */
    public function api_update_schedule(WP_REST_Request $request) {
        $table = $request['table'];
        $this->update_table($table);
        $data = array(
            'code' => 'updated',
            'message' => 'Machine schedule table successfully updated.',
            'data' => array(
                'table' => $table,
            ),
        );
        return json_encode($data);
    }
}

$machine_schedule = MachineSchedule::instance();
?>
