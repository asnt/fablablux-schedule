<?php

include_once(plugin_dir_path(__FILE__) . 'options-view.php');

/**
 * Manage the options for the machine schedule.
 */
class MachineScheduleOptions implements ArrayAccess {

    private static $instance = null;

    /**
     * Name of the key in the options table of the database.
     */
    const key = "machine_schedule";

    /**
     * The default options array.
     */
    private static $default_options = array(
        "page_id" => -1,
        "machine_names" => array(
            "MakerBot 1", "MakerBot 2", "RepRap", "Small CNC", "Big CNC",
            "Laser Cutter", "Vinyl Cutter"
        ),
        "slot_names" => array(
            "13 - 14", "14 - 15", "15 - 16", "16 - 17", "17 - 18", "18 - 19",
            "19 - 20", "20 - 21", "21 - 22"
        ),
        "visible_machines" => array(
            true, true, true, true, true, true, true
        ),
        "visible_slots" => array(
            true, true, true, true, true, true, true, true, true
        ),
        "opening_hours" => array(
            // (day, start_hour, start_minutes, end_hour, end_minutes)
            array("Thursday", 14, 0, 21, 0),
        ),
        "timezone" => "Europe/Luxembourg",
        "_table" => array(
            array(false, false, false, false, false, false, false, false,
                  false),
            array(false, false, false, false, false, false, false, false,
                  false),
            array(false, false, false, false, false, false, false, false,
                  false),
            array(false, false, false, false, false, false, false, false,
                  false),
            array(false, false, false, false, false, false, false, false,
                  false),
            array(false, false, false, false, false, false, false, false,
                  false),
            array(false, false, false, false, false, false, false, false,
                  false),
        ),
    );

    /**
     * The most recent options array.
     */
    private $options = null;

    /**
     * Indicate if the options have already been loaded from the database.
     */
    private $loaded = false;

    public static function instance() {
        if (is_null(self::$instance)) {
            self::$instance = new self;
        }
        return self::$instance;
    }

    private function __construct() {
        $this->init();
    }

    public function register_menu() {
        add_options_page('Machine Schedule Options',
                         'Machine Schedule',
                         'manage_options',
                         'machine-schedule-admin-menu',
                         array($this, 'render_admin_menu'));
    }

    public function render_admin_menu() {
        if (!current_user_can('manage_options')) {
            wp_die(('You do not have sufficient permissions to access this' .
                    ' page.'));
        }

        OptionsView::render();
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
        $options = get_option(self::key);
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
        update_option(self::key, $this->options);
    }

    /**
     * Delete the options from the database.
     */
    public function delete() {
        delete_option(self::key);
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
}

?>
