<?php

include_once(plugin_dir_path(__FILE__) . 'open-access.php');
include_once(plugin_dir_path(__FILE__) . 'options.php');
include_once(plugin_dir_path(__FILE__) . 'table.php');

/**
 * Expose the machine schedule through a REST API.
 */
class MachineScheduleApi {

    private $options = null;

    public function __construct() {
        $this->options = MachineScheduleOptions::instance();
    }

    public function activate() {
        $this->register_routes();
    }

    private function register_routes() {
        add_action('rest_api_init', function() {
            register_rest_route('open-access/v1', '/', array(
                'methods' => 'GET',
                'callback' => array($this, 'get_status'),
            ));
            register_rest_route('open-access/v1', '/machine-schedule', array(
                'methods' => 'GET',
                'callback' => array($this, 'get_schedule'),
            ));
            register_rest_route('open-access/v1', '/machine-schedule', array(
                'methods' => 'POST',
                'callback' => array($this, 'update_schedule'),
                'args' => array(
                    'table' => array(
                        'required' => true,
                    ),
                ),
                'permission_callback' => array($this, 'authenticate'),
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
    public function authenticate(WP_REST_Request $request) {
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
    public function get_status() {
        $data = array(
            'open_access' => OpenAccess::status()
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
    public function get_schedule() {
        $table = Table::get($this->options["page_id"]);
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
    public function update_schedule(WP_REST_Request $request) {
        $table = $request['table'];
        $page_id = $this->options['page_id'];
        $success = Table::update($page_id, $table);
        if ($success) {
            $data = array(
                'code' => 'updated',
                'message' => 'Updated machine schedule.',
                'data' => array(
                    'table' => $table,
                ),
            );
        } else  {
            $data = array(
                'code' => 'update_error',
                'message' => 'Could not update machine schedule.',
                'data' => array(
                    'table' => $table,
                ),
            );
        }
        return json_encode($data);
    }
}

?>
