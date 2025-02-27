import {Tooltip2 as Tooltip} from '@blueprintjs/popover2';
import styled from 'styled-components/macro';

export const WarningTooltip = styled(Tooltip)`
  display: block;
  margin-left: 8px;
  outline: none;

  .bp3-popover-target,
  .bp3-icon {
    display: block;
  }

  .bp3-icon:focus,
  .bp3-icon:active {
    outline: none;
  }
`;
