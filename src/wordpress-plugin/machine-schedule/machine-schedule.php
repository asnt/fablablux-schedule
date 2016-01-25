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

    private $options = null;

    private function __construct() {
        $this->api = new MachineScheduleApi();
        $this->api->activate();

        $this->options = MachineScheduleOptions::instance();

        register_activation_hook(
            __FILE__,
            array('MachineSchedule', 'activate')
        );
        register_uninstall_hook(
            __FILE__,
            array('MachineSchedule', 'uninstall')
        );
        add_action('admin_menu', array($this, 'action_admin_menu'));
        add_filter('the_content', array($this, 'the_content'), 20, 1);
    } 

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
        // By getting the instance, the options are initialized in the
        // database.
        $options = MachineScheduleOptions::instance();
    }

    /**
     * Clear plugin data on uninstallation.
     */
    public static function uninstall() {
        if (!current_user_can('activate_plugins')) {
            return;
        }
        $options = MachineScheduleOptions::intance();
        $options->delete();
    }

    /**
     * Add an options page in the admin menu.
     */
    public function action_admin_menu() {
        $this->options->register_menu();
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
        $table = Table::get_visible($page_id);
        $machine_names = Table::get_visible_machines();
        $slot_names = Table::get_visible_slots();

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
