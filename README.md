# MiniDoods

This project is a fork of [DOODS2](https://github.com/snowzach/doods2) which is reduced to the 
bare minimum of functionality I need for my use case.

Doods(2) is an awesome tool for objection recognition in images, videos, ... with various features.
On top there is a [Home Assistant Integration](https://www.home-assistant.io/integrations/doods/) 
that allows to automatically detect objects in camera streams. But in the context of Home Assistant 
Doods appears to be a bit bloated as it uses significantly more resources as the whole HASS instance.

This project is an attempt to reduce resource usage (especially RAM and disk usage) as far as
possible while still being compatible to the Doods API part used by HASS. Therefore, only the PyTorch
detector is available and the image no longer utilizes specialized hardware.