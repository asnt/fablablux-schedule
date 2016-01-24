<?php
/*
Plugin Name: FabLabLux Machine Schedule
Description: Display the machine schedule on a page during open access hours.
Author: Alexandre Saint
Version: 1.0
*/

defined('ABSPATH') or exit; 

include_once(plugin_dir_path(__FILE__) . 'open-access.php');
include_once(plugin_dir_path(__FILE__) . 'options.php');
include_once(plugin_dir_path(__FILE__) . 'rest-api.php');
include_once(plugin_dir_path(__FILE__) . 'table.php');

/**
 * Display the machine use schedule during open access time.
 *
 * TODO:
 *
 * - Record and display a timestamp of the table update.
 * - Make the wordpress cookie authentication work.
 *   Probably requires the use of nonces with action 'wp_json'. Create the
 *   nonce on the server with wp_create_nonce('wp_json'). Pass it along to
 *   the client somehow. The client includes the header 'X-WP-Nonce' with the
 *   value of the nonce in every header.
 */
class MachineSchedule {

    static $instance = null;

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

    private function __construct() {
        $this->api = new MachineScheduleApi();
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

        $this->options = MachineScheduleOptions::instance();
    } 

    /**
     * Get the singleton instance of this class.
     *
     * The instance is created if it does not exist yet.
     *
     * @return MachineSchedule
     */
    public static function instance() {
        if (is_null(self::$instance)) {
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
        // The instanciation initialises the options in the database.
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
     * Get the latest schedule with visible machines and slots only.
     *
     * @return array array("table" => array(),         // M x N
     *                     "machine_names" => array(), // M
     *                     "slot_names" => array(),    // N
     *                     )
     */
    private function get_visible_schedule() {
        $table = Table::get($this->options['page_id']);
        $machine_names = $this->options['machine_names'];
        $slot_names = $this->options['slot_names'];
        $machine_mask = $this->options['visible_machines'];
        $slot_mask = $this->options['visible_slots'];

        $masked_rows = $this->filter_rows($table, $machine_mask);
        $masked_table = $this->filter_columns($masked_rows, $slot_mask);
        $masked_machine_names = $this->filter_rows($machine_names,
                                                   $machine_mask);
        $masked_slot_names = $this->filter_rows($slot_names, $slot_mask);

        $schedule = array(
            "table" => $masked_table,
            "machine_names" => $masked_machine_names,
            "slot_names" => $masked_slot_names,
        );

        return $schedule;
    }

    /**
     * Filter the rows of an array using the given mask.
     *
     * The mask must be the same length as the number of rows in the array. If
     * not, the $array is returned as is.
     *
     * @return array
     */
    private function filter_rows($array, $row_mask) {
        $n_rows = count($array);
        if ($n_rows != count($row_mask)) {
            return $array;
        }

        $filtered_array = array();

        for($index = 0; $index < $n_rows; $index++) {
            if($row_mask[$index]) {
                array_push($filtered_array, $array[$index]);
            }
        }

        return $filtered_array;
    }

    /**
     * Filter the columns of an array using the given mask.
     *
     * The mask must be the same length as the number of columns in the array.
     * If not, the $array is returned as is.
     *
     * @return array
     */
    private function filter_columns($array, $col_mask) {
        $n_rows = count($array);
        if($n_rows == 0) {
            return $array;
        }

        $n_cols = count($array[0]);
        if ($n_cols != count($col_mask)) {
            return $array;
        }

        $filtered_array = array();

        for($row = 0; $row < $n_rows; $row++) {
            $row_array = array();
            for($col = 0; $col < $n_cols; $col++) {
                if($col_mask[$col]) {
                    array_push($row_array, $array[$row][$col]);
                }
            }
            array_push($filtered_array, $row_array);
        }

        return $filtered_array;
    }

    /**
     * Display the machine schedule table at the end of the content.
     *
     * @param string $content The original content.
     * @return string The modified content.
     */
    public function the_content($content) {
        if (!OpenAccess::status()) {
            return $content;
        }

        $page_id = $this->options['page_id'];
        if (!is_page($page_id)) {
            return $content;
        }

        // Get the schedule data.
        $schedule = $this->get_visible_schedule();
        $table = $schedule['table'];
        $machine_names = $schedule['machine_names'];
        $slot_names = $schedule['slot_names'];

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
}

$machine_schedule = MachineSchedule::instance();

?>
