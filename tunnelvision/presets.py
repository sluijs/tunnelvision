__all__ = ['Window']

from enum import Enum

class Window(Enum):
    """
    An enumeration of commonly used window settings for CT viewing.
    Each member returns a dictionary with 'center' and 'width' values.
    These settings are designed to be passed directly to a function
    that expects a configuration dictionary in the format:
    {'window': {'center': value, 'width': value}}.
    """

    # Soft Tissue Window: Good for general soft tissue visualization.
    SOFT_TISSUE = {'center': 50, 'width': 400}

    # Brain Window: Optimized for viewing brain parenchyma and subtle changes.
    BRAIN = {'center': 40, 'width': 80}

    # Lung Window: Designed for visualizing lung parenchyma, airways, and subtle nodules.
    LUNG = {'center': -600, 'width': 1500}

    # Bone Window: Ideal for detailed visualization of bone structures, fractures, and lesions.
    BONE = {'center': 400, 'width': 1500}

    # Liver Window: Specific for liver parenchyma and lesions.
    LIVER = {'center': 60, 'width': 150}

    # Abdomen Window: General window for abdominal organs.
    ABDOMEN = {'center': 40, 'width': 350}

    # Mediastinum Window: For visualizing structures in the mediastinum (heart, great vessels).
    MEDIASTINUM = {'center': 40, 'width': 400}

    # Stroke (Acute Ischemic) Window: A narrower window to enhance subtle changes in acute stroke.
    STROKE = {'center': 35, 'width': 40}

    # Subdural Window: For better visualization of subdural hematomas.
    SUBDURAL = {'center': 100, 'width': 200}

    # Angio (CTA) Window: For visualizing contrast-enhanced vessels.
    ANGIO = {'center': 300, 'width': 600}

    def get_config(self):
        """
        Returns the window configuration dictionary for the current setting,
        formatted as {'window': {'center': value, 'width': value}}.

        Returns:
            dict: A dictionary containing the 'window' key with 'center' and 'width' values.
        """
        return {'window': self.value}