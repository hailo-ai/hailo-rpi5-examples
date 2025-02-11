import onnxruntime as ort
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams,
    InputVStreamParams, OutputVStreamParams, InputVStreams, OutputVStreams, FormatType)
import time
class SingletonMeta(type):
    """
    This is a thread-safe implementation of Singleton.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class create_target(metaclass=SingletonMeta):
    def __init__(self):
        self.target = VDevice()
    def get_device(self):
        return self.target

class Hailo():

    def __init__(self, hef_path ,input_dtype, output_dtype):
        self.target = create_target().get_device()
        hef = HEF(hef_path)

        configure_params = ConfigureParams.create_from_hef(hef=hef, interface=HailoStreamInterface.PCIe)
        self.network_groups = self.target.configure(hef, configure_params)
        self.network_group = self.network_groups[0]
        self.network_group_params = self.network_group.create_params()

        # Create input and output virtual streams params
        self.input_vstreams_params = InputVStreamParams.make(self.network_group, format_type=input_dtype)
        self.output_vstreams_params = OutputVStreamParams.make(self.network_group, format_type=output_dtype)

        self.input_vstream_info = hef.get_input_vstream_infos()
        self.output_vstream_info = hef.get_output_vstream_infos()

        self.running = True  # Flag to control generator execution
        self.infer_gen = self._infer()  # Create the generator object

    def _infer(self):
        with InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params) as infer_pipeline:
            with self.network_group.activate(self.network_group_params):
                while self.running:
                    input_frame = yield  # Receive input frame
                    if input_frame is None:  # Check for termination signal
                        self.running = False
                    else:
                        yield infer_pipeline.infer(input_frame)

    def infer(self, input_frame):
        next(self.infer_gen)
        return self.infer_gen.send(input_frame)
    
    def infer_slow(self, input_frame):
        with InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params) as infer_pipeline:
            with self.network_group.activate(self.network_group_params):
                return infer_pipeline.infer(input_frame)

    def deactivate_network(self):
        if self.running:
            self.infer_gen.send(None)


